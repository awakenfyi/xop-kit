"""
base.py — Guard interface for the xOP framework.

A Guard is a deterministic scanner. No model, no judgment.
Input: text. Output: JSON flag report. REVIEW/PASS/FAIL.

A Guard that requires judgment is not a Guard — it's a misclassified xOP.
"""
from __future__ import annotations

import json
import time
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Flag:
    """A single finding from a Guard scan."""
    rule_id: str        # e.g. "vocabulary.delve" or "construction.not_just_but"
    tier: str           # "vocabulary" | "construction" | "rhythm"
    severity: str       # "review" | "deny" (deny = hard fail, review = needs xOP judgment)
    match: str          # the offending text
    line: int           # 1-based line number
    context: str = ""   # surrounding sentence for xOP judgment


@dataclass
class GuardReport:
    """Standard output from any Guard."""
    guard_id: str
    version: str
    verdict: str = "PASS"                    # PASS | REVIEW | FAIL
    flags: list = field(default_factory=list)  # list[Flag]
    advisory: dict = field(default_factory=dict)  # non-gating metrics (rhythm, etc.)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["flags"] = [asdict(f) for f in self.flags]
        return d

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @property
    def has_denials(self) -> bool:
        return any(f.severity == "deny" for f in self.flags)

    @property
    def has_reviews(self) -> bool:
        return any(f.severity == "review" for f in self.flags)


class Guard(ABC):
    """
    Abstract base for all Guards.

    Subclass this and implement:
      - guard_id: str
      - version: str
      - scan(text, **kwargs) -> GuardReport
    """

    @property
    @abstractmethod
    def guard_id(self) -> str:
        ...

    @property
    @abstractmethod
    def version(self) -> str:
        ...

    @abstractmethod
    def scan(self, text: str, **kwargs) -> GuardReport:
        ...

    def run(self, text: str, **kwargs) -> GuardReport:
        """Run scan with timing and metadata."""
        start = time.monotonic()
        report = self.scan(text, **kwargs)

        # Compute verdict from flags
        if report.has_denials:
            report.verdict = "FAIL"
        elif report.has_reviews:
            report.verdict = "REVIEW"
        else:
            report.verdict = "PASS"

        # Add metadata
        words = text.split()
        report.metadata.update({
            "input_words": len(words),
            "input_hash": hashlib.sha256(text.encode()).hexdigest()[:12],
            "scan_ms": round((time.monotonic() - start) * 1000, 1),
        })

        return report


def run_guard_cli(guard: Guard):
    """Standard CLI entry point for any Guard."""
    import argparse
    import sys
    from pathlib import Path

    parser = argparse.ArgumentParser(description=f"Run {guard.guard_id} Guard")
    parser.add_argument("file", nargs="?", default="-",
                        help="File to scan (- for stdin)")
    parser.add_argument("--json", action="store_true",
                        help="JSON output")
    parser.add_argument("--fixtures", type=Path,
                        help="Run self-test against fixture file")
    parser.add_argument("--profile", type=Path,
                        help="Custom rule profile (JSON)")
    args = parser.parse_args()

    if args.fixtures:
        passed, failed = run_fixtures(guard, args.fixtures)
        print(f"\n{passed}/{passed + failed} fixtures passed.")
        sys.exit(1 if failed else 0)

    if args.file == "-":
        text = sys.stdin.read()
    else:
        text = Path(args.file).read_text()

    report = guard.run(text)

    if args.json:
        print(report.to_json())
    else:
        print(format_human(report))

    sys.exit(0 if report.verdict == "PASS" else 1)


def run_fixtures(guard: Guard, path) -> tuple:
    """Run Guard against a JSONL fixture file. Returns (passed, failed)."""
    from pathlib import Path
    cases = [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]
    passed = failed = 0

    for c in cases:
        report = guard.run(c["text"])
        got_verdict = report.verdict
        want_verdict = c["expect_verdict"]

        # Check specific tells if specified
        want_tells = set(c.get("expect_tells", []))
        got_tells = {f.rule_id for f in report.flags}
        tells_ok = want_tells.issubset(got_tells)

        ok = (got_verdict == want_verdict) and tells_ok
        passed += ok
        failed += not ok

        status = "PASS" if ok else "FAIL"
        label = c.get("label", "unlabeled")
        print(f"  [{status}] {label}: expected={want_verdict} got={got_verdict}"
              + (f" missing_tells={want_tells - got_tells}" if not tells_ok else ""))

    return passed, failed


def format_human(report: GuardReport) -> str:
    """Human-readable Guard report."""
    out = [f"VERDICT: {report.verdict}   ({len(report.flags)} flags)"]

    if report.flags:
        denials = [f for f in report.flags if f.severity == "deny"]
        reviews = [f for f in report.flags if f.severity == "review"]

        if denials:
            out.append("\nDENY (hard failures — violate explicit rules):")
            for f in denials:
                out.append(f'  L{f.line:<4} [{f.rule_id}]  “{f.match}”')

        if reviews:
            out.append("\nREVIEW (candidates — need xOP judgment):")
            for f in reviews:
                ctx = f'  | {f.context}' if f.context else ''
                out.append(f'  L{f.line:<4} [{f.rule_id}]  “{f.match}”{ctx}')

    if report.advisory:
        out.append("\nAdvisory (not gating):")
        for k, v in report.advisory.items():
            out.append(f"  {k}: {v}")

    out.append(f"\nNote: REVIEW flags are candidates. Judgment is the xOP's job, not the Guard's.")
    return "\n".join(out)
