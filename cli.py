#!/usr/bin/env python3
"""
xop — CLI for the xOP behavioral governance framework.

Usage:
    xop scan draft.md                    # Run all Guards against a file
    xop scan draft.md --pack writing     # Run a specific Work Pack
    xop scan draft.md --guard closure    # Run a specific Guard
    xop scan - < draft.txt               # Read from stdin
    xop test                             # Run all fixture tests
    xop test --pack writing              # Test a specific Work Pack
    xop list                             # List registered Work Packs
    xop info writing                     # Show Work Pack details

Exit codes:
    0  PASS    — no flags
    1  REVIEW  — flags found, need xOP judgment
    2  FAIL    — hard failures (deny-severity flags)
    3  GATE    — gate violation detected
    4  ERROR   — usage or runtime error

Agent-first:
    Auto-JSON when piped (stdout is not a terminal).
    --compact returns only high-gravity fields (flag count, verdict, rule IDs).
    Typed exit codes let agents self-correct without parsing text.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Framework root
FRAMEWORK_ROOT = Path(__file__).parent
sys.path.insert(0, str(FRAMEWORK_ROOT))

from guards.base import GuardReport, format_human, run_fixtures
from guards.no_ai_tells import NoAiTellsGuard
from guards.agreement_bias import AgreementBiasGuard
from guards.closure_rush import ClosureRushGuard
from guards.helpful_explosion import HelpfulExplosionGuard
from guards.coaching import CoachingGuard
from guards.template_cascade import TemplateCascadeGuard
from guards.stance_calibration import StanceCalibrationGuard

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
GUARDS = {
    "no-ai-tells":        NoAiTellsGuard,
    "writing":            NoAiTellsGuard,       # alias
    "agreement-bias":     AgreementBiasGuard,
    "agreement":          AgreementBiasGuard,    # alias
    "closure-rush":       ClosureRushGuard,
    "closure":            ClosureRushGuard,      # alias
    "helpful-explosion":  HelpfulExplosionGuard,
    "helpful":            HelpfulExplosionGuard,  # alias
    "coaching":           CoachingGuard,
    "template-cascade":   TemplateCascadeGuard,
    "template":           TemplateCascadeGuard,  # alias
    "stance-calibration": StanceCalibrationGuard,
    "stance":             StanceCalibrationGuard, # alias
}

# Canonical names only (no aliases)
CANONICAL = {
    "writing":   {"guard": "no-ai-tells",        "xop": "writing-license",      "shadow": None,  "fixtures": "writing_fixtures.jsonl"},
    "agreement": {"guard": "agreement-bias",      "xop": "agreement-calibration", "shadow": "S-01", "fixtures": "agreement_bias_fixtures.jsonl"},
    "closure":   {"guard": "closure-rush",        "xop": "closure-rush",         "shadow": "S-07", "fixtures": "closure_rush_fixtures.jsonl"},
    "helpful":   {"guard": "helpful-explosion",   "xop": "helpful-explosion",    "shadow": "S-02", "fixtures": "helpful_explosion_fixtures.jsonl"},
    "coaching":  {"guard": "coaching",            "xop": "coaching-calibration", "shadow": "S-04", "fixtures": "coaching_fixtures.jsonl"},
    "template":  {"guard": "template-cascade",    "xop": "template-cascade",     "shadow": "S-03", "fixtures": "template_cascade_fixtures.jsonl"},
    "stance":    {"guard": "stance-calibration",  "xop": "stance-calibration",   "shadow": None,  "fixtures": "stance_calibration_fixtures.jsonl"},
}

# Exit codes
EXIT_PASS   = 0
EXIT_REVIEW = 1
EXIT_FAIL   = 2
EXIT_GATE   = 3
EXIT_ERROR  = 4


def _is_piped() -> bool:
    """Auto-detect JSON mode when stdout is piped."""
    return not sys.stdout.isatty()


def _read_input(file_arg: str) -> str:
    if file_arg == "-":
        return sys.stdin.read()
    p = Path(file_arg)
    if not p.exists():
        print(f"xop: file not found: {file_arg}", file=sys.stderr)
        sys.exit(EXIT_ERROR)
    return p.read_text()


def _exit_code(verdict: str) -> int:
    return {"PASS": EXIT_PASS, "REVIEW": EXIT_REVIEW, "FAIL": EXIT_FAIL}.get(verdict, EXIT_ERROR)


def _compact_report(report: GuardReport) -> dict:
    """High-gravity fields only — 60-80% fewer tokens."""
    return {
        "guard": report.guard_id,
        "verdict": report.verdict,
        "flags": len(report.flags),
        "rules": list({f.rule_id for f in report.flags}),
    }


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def cmd_scan(args):
    text = _read_input(args.file)
    use_json = args.json or _is_piped()

    # Determine which guards to run
    if args.guard:
        guard_cls = GUARDS.get(args.guard)
        if not guard_cls:
            print(f"xop: unknown guard '{args.guard}'. Available: {', '.join(CANONICAL.keys())}", file=sys.stderr)
            sys.exit(EXIT_ERROR)
        guards = [(args.guard, guard_cls())]
    elif args.pack:
        pack = CANONICAL.get(args.pack)
        if not pack:
            print(f"xop: unknown pack '{args.pack}'. Available: {', '.join(CANONICAL.keys())}", file=sys.stderr)
            sys.exit(EXIT_ERROR)
        guard_cls = GUARDS[pack["guard"]]
        guards = [(args.pack, guard_cls())]
    else:
        # Run all (skip stance — it needs conversation input)
        guards = []
        for name, info in CANONICAL.items():
            if name == "stance":
                continue
            guard_cls = GUARDS[info["guard"]]
            guards.append((name, guard_cls()))

    reports = []
    for name, guard in guards:
        report = guard.run(text)
        reports.append(report)

    # Output
    worst = "PASS"
    for r in reports:
        if r.verdict == "FAIL":
            worst = "FAIL"
        elif r.verdict == "REVIEW" and worst != "FAIL":
            worst = "REVIEW"

    if use_json:
        if args.compact:
            output = [_compact_report(r) for r in reports]
        else:
            output = [r.to_dict() for r in reports]
        print(json.dumps(output if len(reports) > 1 else output[0], indent=2))
    else:
        for r in reports:
            if len(reports) > 1:
                print(f"\n{'='*50}")
                print(f"  {r.guard_id} v{r.version}")
                print(f"{'='*50}")
            if args.compact:
                c = _compact_report(r)
                print(f"{c['verdict']}  {c['flags']} flags  {c['rules']}")
            else:
                print(format_human(r))

    sys.exit(_exit_code(worst))


def cmd_test(args):
    fixture_dir = FRAMEWORK_ROOT / "tests" / "fixtures"

    if args.pack:
        pack = CANONICAL.get(args.pack)
        if not pack:
            print(f"xop: unknown pack '{args.pack}'", file=sys.stderr)
            sys.exit(EXIT_ERROR)
        packs = [(args.pack, pack)]
    else:
        packs = list(CANONICAL.items())

    total_passed = total_failed = 0
    missing = []

    for name, info in packs:
        guard_cls = GUARDS[info["guard"]]
        guard = guard_cls()
        fixture_path = fixture_dir / info["fixtures"]

        if not fixture_path.exists():
            print(f"\n  [{name}] MISSING fixtures: {fixture_path}", file=sys.stderr)
            missing.append(name)
            continue

        print(f"\n{'='*50}")
        print(f"  {name} ({info['guard']})")
        print(f"{'='*50}")
        passed, failed = run_fixtures(guard, fixture_path)
        total_passed += passed
        total_failed += failed

    print(f"\n{'='*50}")
    print(f"  TOTAL: {total_passed}/{total_passed + total_failed} passed")
    print(f"{'='*50}")

    if missing:
        print(f"\nFAIL: {len(missing)} pack(s) had no fixtures: {', '.join(missing)}.",
              file=sys.stderr)
        print("Fixtures ship in the repo, not the installed package — run `xop test` "
              "from a git checkout (git clone + pip install -e .).", file=sys.stderr)
        sys.exit(1)

    if total_passed == 0:
        print("\nFAIL: zero fixtures ran. A 0/0 result is not a pass.", file=sys.stderr)
        sys.exit(1)

    sys.exit(0 if total_failed == 0 else 1)


def cmd_list(args):
    use_json = args.json or _is_piped()

    if use_json:
        print(json.dumps(CANONICAL, indent=2))
    else:
        print("\nxOP Work Packs (Wave 1)")
        print(f"{'='*50}")
        for name, info in CANONICAL.items():
            shadow = f"  ({info['shadow']})" if info['shadow'] else ""
            print(f"  {name:<12}  guard: {info['guard']:<22}  xop: {info['xop']}{shadow}")
        print(f"\nRun: xop scan <file> --pack <name>")
        print(f"Test: xop test --pack <name>")


def cmd_info(args):
    pack = CANONICAL.get(args.pack)
    if not pack:
        print(f"xop: unknown pack '{args.pack}'. Available: {', '.join(CANONICAL.keys())}", file=sys.stderr)
        sys.exit(EXIT_ERROR)

    xop_path = FRAMEWORK_ROOT / "xops" / f"{pack['xop'].replace('-', '_')}.md"
    if not xop_path.exists():
        # Try with hyphens
        xop_path = FRAMEWORK_ROOT / "xops" / f"{pack['xop']}.md"

    print(f"\nWork Pack: {args.pack}")
    print(f"Guard: {pack['guard']}")
    print(f"xOP: {pack['xop']}")
    print(f"Shadow pattern: {pack['shadow'] or 'N/A'}")
    print(f"Fixtures: {pack['fixtures']}")

    if xop_path.exists():
        print(f"\n--- xOP Spec ---\n")
        print(xop_path.read_text())


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        prog="xop",
        description="xOP Framework — behavioral governance for AI output",
        epilog="Lyra Labs. Built to be wrongable.",
    )
    parser.add_argument("--json", action="store_true", help="Force JSON output")
    parser.add_argument("--compact", action="store_true", help="High-gravity fields only (fewer tokens)")

    sub = parser.add_subparsers(dest="command", help="Command")

    # scan
    p_scan = sub.add_parser("scan", help="Scan text against Guards")
    p_scan.add_argument("file", help="File to scan (- for stdin)")
    p_scan.add_argument("--guard", help="Run a specific Guard")
    p_scan.add_argument("--pack", help="Run a specific Work Pack")
    p_scan.add_argument("--json", action="store_true", dest="json", help="Force JSON output")
    p_scan.add_argument("--compact", action="store_true", help="High-gravity fields only")

    # test
    p_test = sub.add_parser("test", help="Run fixture tests")
    p_test.add_argument("--pack", help="Test a specific Work Pack")

    # list
    p_list = sub.add_parser("list", help="List registered Work Packs")
    p_list.add_argument("--json", action="store_true", dest="json", help="JSON output")

    # info
    p_info = sub.add_parser("info", help="Show Work Pack details")
    p_info.add_argument("pack", help="Work Pack name")

    args = parser.parse_args()

    if args.command == "scan":
        cmd_scan(args)
    elif args.command == "test":
        cmd_test(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "info":
        cmd_info(args)
    else:
        parser.print_help()
        sys.exit(EXIT_ERROR)


if __name__ == "__main__":
    main()
