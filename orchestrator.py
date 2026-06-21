#!/usr/bin/env python3
"""
orchestrator.py — Wires Guards → xOPs → Resolution.

CLI usage:
    python orchestrator.py draft.md --pack writing
    python orchestrator.py draft.md --guard no-ai-tells
    python orchestrator.py draft.md --all --json

As a library:
    from orchestrator import Pipeline
    pipe = Pipeline.from_registry("registry.json")
    result = pipe.run_guard("no-ai-tells", text)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add framework root to path
sys.path.insert(0, str(Path(__file__).parent))

from guards.base import GuardReport
from guards.no_ai_tells import NoAiTellsGuard
from guards.agreement_bias import AgreementBiasGuard
from guards.closure_rush import ClosureRushGuard
from guards.helpful_explosion import HelpfulExplosionGuard
from guards.coaching import CoachingGuard
from guards.template_cascade import TemplateCascadeGuard
from guards.stance_calibration import StanceCalibrationGuard
from xops.base import XopReport, Disposition, ResolutionReport


# ---------------------------------------------------------------------------
# Guard Registry — maps guard_id to Guard instances
# ---------------------------------------------------------------------------
GUARD_REGISTRY = {
    "no-ai-tells": NoAiTellsGuard,
    "agreement-bias": AgreementBiasGuard,
    "closure-rush": ClosureRushGuard,
    "helpful-explosion": HelpfulExplosionGuard,
    "coaching": CoachingGuard,
    "template-cascade": TemplateCascadeGuard,
    "stance-calibration": StanceCalibrationGuard,
}


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
class Pipeline:
    """Orchestrates Guard → xOP → Resolution."""

    def __init__(self, registry_path: Path = None):
        self.registry = {}
        if registry_path and registry_path.exists():
            self.registry = json.loads(registry_path.read_text())

    def run_guard(self, guard_id: str, text: str, **kwargs) -> GuardReport:
        """Run a single Guard and return its report."""
        guard_cls = GUARD_REGISTRY.get(guard_id)
        if not guard_cls:
            raise ValueError(f"Unknown guard: {guard_id}. Available: {list(GUARD_REGISTRY.keys())}")
        guard = guard_cls(**kwargs)
        return guard.run(text)

    def run_all_guards(self, text: str) -> list:
        """Run all registered Guards. Returns list of GuardReports.

        Skips stance-calibration — it is an evaluation xOP that requires
        conversation history, not single-text input.
        """
        reports = []
        for guard_id, guard_cls in GUARD_REGISTRY.items():
            if guard_id == "stance-calibration":
                continue
            guard = guard_cls()
            reports.append(guard.run(text))
        return reports

    def run_pack(self, pack_name: str, text: str) -> dict:
        """
        Run a complete Work Pack (Guard + placeholder for xOP).
        Returns the Guard report. xOP judgment requires an LLM agent
        and is handled by the orchestrator_agent, not this script.
        """
        pack = self.registry.get("work_packs", {}).get(pack_name)
        if not pack:
            # Fall back to guard-only mode
            return {"guard": self.run_guard(pack_name, text).to_dict()}

        guard_id = pack["guard"]
        guard_report = self.run_guard(guard_id, text)

        return {
            "pack": pack_name,
            "guard": guard_report.to_dict(),
            "xop_required": guard_report.verdict == "REVIEW",
            "xop_id": pack.get("xop"),
            "note": "xOP judgment requires an LLM agent — see agents/xop_agent.md"
        }


def main():
    parser = argparse.ArgumentParser(
        description="xOP Framework Orchestrator — run Guards and Work Packs"
    )
    parser.add_argument("file", nargs="?", default="-",
                        help="File to scan (- for stdin)")
    parser.add_argument("--guard", type=str,
                        help="Run a specific Guard by ID")
    parser.add_argument("--pack", type=str,
                        help="Run a complete Work Pack by name")
    parser.add_argument("--all", action="store_true",
                        help="Run all registered Guards")
    parser.add_argument("--json", action="store_true",
                        help="JSON output")
    parser.add_argument("--registry", type=Path,
                        default=Path(__file__).parent / "registry.json",
                        help="Path to registry.json")
    args = parser.parse_args()

    # Read input
    if args.file == "-":
        text = sys.stdin.read()
    else:
        text = Path(args.file).read_text()

    pipe = Pipeline(args.registry)

    # Execute
    if args.guard:
        report = pipe.run_guard(args.guard, text)
        if args.json:
            print(report.to_json())
        else:
            from guards.base import format_human
            print(format_human(report))
        sys.exit(0 if report.verdict == "PASS" else 1)

    elif args.pack:
        result = pipe.run_pack(args.pack, text)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["guard"]["verdict"] == "PASS" else 1)

    elif args.all:
        reports = pipe.run_all_guards(text)
        if args.json:
            print(json.dumps([r.to_dict() for r in reports], indent=2))
        else:
            for r in reports:
                from guards.base import format_human
                print(f"\n{'='*60}")
                print(f"Guard: {r.guard_id} v{r.version}")
                print(f"{'='*60}")
                print(format_human(r))
        any_fail = any(r.verdict != "PASS" for r in reports)
        sys.exit(1 if any_fail else 0)

    else:
        # Default: run all guards
        reports = pipe.run_all_guards(text)
        for r in reports:
            from guards.base import format_human
            print(format_human(r))
        any_fail = any(r.verdict != "PASS" for r in reports)
        sys.exit(1 if any_fail else 0)


if __name__ == "__main__":
    main()
