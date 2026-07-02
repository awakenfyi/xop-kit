#!/usr/bin/env python3
"""
xop — CLI for the xOP behavioral governance framework.

Usage:
    xop scan draft.md                    # Run all Guards against a file
    xop scan draft.md --pack writing     # Run a specific Work Pack
    xop scan draft.md --guard closure    # Run a specific Guard
    xop scan - < draft.txt               # Read from stdin
    xop test                             # Run all fixture tests (Guard + conduct if present)
    xop test --pack writing              # Test a specific Work Pack
    xop test --rule done-means-verified  # Test a specific conduct rule
    xop list                             # List registered Work Packs
    xop info writing                     # Show Work Pack details
    xop init my-agent                    # Scaffold a new conduct-first agent
    xop wrap ./existing-agent            # Add conduct/ to an existing agent
    xop add-rule                         # Interactively author a new conduct rule

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
        # Auto-detect: if conduct/guards.yaml exists in cwd, use those guards
        conduct_guards_yaml = Path.cwd() / "conduct" / "guards.yaml"
        if conduct_guards_yaml.exists():
            guards = []
            for line in conduct_guards_yaml.read_text().splitlines():
                line = line.strip()
                if line.startswith("- "):
                    gid = line[2:].split("#")[0].strip()
                    if gid and gid in GUARDS:
                        guards.append((gid, GUARDS[gid]()))
                    elif gid:
                        print(f"xop: guard '{gid}' in conduct/guards.yaml not found in registry", file=sys.stderr)
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
    rule_id = getattr(args, "rule", None)
    conduct_dir = Path.cwd() / "conduct"

    # --rule <id>: conduct-only test
    if rule_id:
        if not conduct_dir.exists():
            print("xop: no conduct/ directory found. Run from inside an agent directory.", file=sys.stderr)
            sys.exit(EXIT_ERROR)
        passed, failed, missing = _run_conduct_tests(conduct_dir, rule_id)
        _print_conduct_summary(passed, failed, missing)
        sys.exit(0 if failed == 0 and not missing else 1)

    # --pack <name>: Guard-only test
    if args.pack:
        fixture_dir = FRAMEWORK_ROOT / "tests" / "fixtures"
        pack = CANONICAL.get(args.pack)
        if not pack:
            print(f"xop: unknown pack '{args.pack}'", file=sys.stderr)
            sys.exit(EXIT_ERROR)
        packs = [(args.pack, pack)]
        total_passed = total_failed = 0
        missing = []
        guard_cls = GUARDS[pack["guard"]]
        guard = guard_cls()
        fixture_path = fixture_dir / pack["fixtures"]
        if not fixture_path.exists():
            print(f"\n  [{args.pack}] MISSING fixtures: {fixture_path}", file=sys.stderr)
            missing = [args.pack]
        else:
            print(f"\n{'='*50}")
            print(f"  {args.pack} ({pack['guard']})")
            print(f"{'='*50}")
            total_passed, total_failed = run_fixtures(guard, fixture_path)
        print(f"\n{'='*50}")
        print(f"  TOTAL: {total_passed}/{total_passed + total_failed} passed")
        print(f"{'='*50}")
        if missing:
            print(f"\nFAIL: missing fixtures. Fixtures ship in the repo — run from a git checkout.",
                  file=sys.stderr)
            sys.exit(1)
        sys.exit(0 if total_failed == 0 else 1)

    # No flags: run Guard fixtures + conduct rules if present
    guard_passed = guard_failed = 0
    guard_missing = []
    fixture_dir = FRAMEWORK_ROOT / "tests" / "fixtures"

    for name, info in CANONICAL.items():
        guard_cls = GUARDS[info["guard"]]
        guard = guard_cls()
        fixture_path = fixture_dir / info["fixtures"]
        if not fixture_path.exists():
            print(f"\n  [{name}] MISSING fixtures: {fixture_path}", file=sys.stderr)
            guard_missing.append(name)
            continue
        print(f"\n{'='*50}")
        print(f"  {name} ({info['guard']})")
        print(f"{'='*50}")
        p, f = run_fixtures(guard, fixture_path)
        guard_passed += p
        guard_failed += f

    conduct_passed = conduct_failed = 0
    conduct_missing = []
    ran_conduct = False
    if conduct_dir.exists():
        ran_conduct = True
        conduct_passed, conduct_failed, conduct_missing = _run_conduct_tests(conduct_dir)

    total_passed = guard_passed + conduct_passed
    total_failed = guard_failed + conduct_failed
    all_missing = guard_missing + conduct_missing

    print(f"\n{'='*50}")
    print(f"  TOTAL: {total_passed}/{total_passed + total_failed} passed")
    if ran_conduct:
        print(f"  (guards: {guard_passed}/{guard_passed+guard_failed}  "
              f"conduct: {conduct_passed}/{conduct_passed+conduct_failed})")
    print(f"{'='*50}")

    if all_missing:
        print(f"\nFAIL: {len(all_missing)} pack(s)/rule(s) had no fixtures: {', '.join(all_missing)}.",
              file=sys.stderr)
        if guard_missing:
            print("Guard fixtures ship in the repo — run from a git checkout "
                  "(git clone + pip install -e .).", file=sys.stderr)
        sys.exit(1)

    if total_passed == 0:
        print("\nFAIL: zero fixtures ran. A 0/0 result is not a pass.", file=sys.stderr)
        sys.exit(1)

    sys.exit(0 if total_failed == 0 else 1)


def _parse_rule_id(rule_path: Path) -> str:
    """Extract the id from YAML frontmatter."""
    for line in rule_path.read_text().splitlines():
        if line.startswith("id:"):
            return line.split(":", 1)[1].strip()
    return rule_path.stem


def _load_registry() -> dict:
    p = FRAMEWORK_ROOT / "registry.json"
    return json.loads(p.read_text()) if p.exists() else {}


def _valid_guard_ids() -> set:
    """All guard ids and pack names from registry.json."""
    reg = _load_registry()
    packs = reg.get("work_packs", {})
    return set(packs.keys()) | {info["guard"] for info in packs.values()}


def _lint_pair(hold_path: Path, drop_path: Path) -> list:
    """Check held-response-constant contract. Returns list of error strings."""
    hold = json.loads(hold_path.read_text())
    drop = json.loads(drop_path.read_text())
    errors = []

    ht = hold.get("turns", [])
    dt = drop.get("turns", [])

    if len(ht) != len(dt):
        errors.append(f"turn count differs: hold={len(ht)} drop={len(dt)}")
        return errors
    if len(ht) < 2:
        errors.append("fixture must have at least 2 turns")
        return errors

    # Prefix: all turns except last two
    for i, (h, d) in enumerate(zip(ht[:-2], dt[:-2])):
        if h != d:
            errors.append(f"turn {i} (prefix) differs — must be identical; "
                          f"hold={h['content']!r:.60} drop={d['content']!r:.60}")

    # Final assistant turn must be identical
    if ht[-1] != dt[-1]:
        errors.append(f"turn {len(ht)-1} (final assistant) differs — must be held constant; "
                      f"hold={ht[-1]['content']!r:.60} drop={dt[-1]['content']!r:.60}")

    # Final user turn must differ
    if ht[-2] == dt[-2]:
        errors.append(f"turn {len(ht)-2} (final user) is identical — "
                      f"hold and drop must differ here")

    # trigger_present_at_final flags
    if hold.get("trigger_present_at_final") is not True:
        errors.append("hold fixture: trigger_present_at_final must be true")
    if drop.get("trigger_present_at_final") is not False:
        errors.append("drop fixture: trigger_present_at_final must be false")

    return errors


def _validate_guards_yaml(conduct_dir: Path) -> list:
    """Check every id in guards.yaml resolves in registry.json. Returns error strings."""
    guards_yaml = conduct_dir / "guards.yaml"
    if not guards_yaml.exists():
        return []
    valid = _valid_guard_ids()
    errors = []
    for line in guards_yaml.read_text().splitlines():
        line = line.strip()
        if line.startswith("- "):
            gid = line[2:].split("#")[0].strip()
            if gid and gid not in valid:
                errors.append(f"unresolvable guard id '{gid}' in conduct/guards.yaml "
                               f"(valid: {', '.join(sorted(valid))})")
    return errors


def _run_conduct_tests(conduct_dir: Path, rule_id: str = None):
    """Run hold/drop fixtures for conduct rules. Returns (passed, failed, missing)."""
    # Validate guards.yaml first
    guard_errors = _validate_guards_yaml(conduct_dir)
    if guard_errors:
        for e in guard_errors:
            print(f"  FAIL: {e}", file=sys.stderr)
        return 0, len(guard_errors), []

    if rule_id:
        rule_files = [conduct_dir / f"{rule_id}.md"]
        if not rule_files[0].exists():
            print(f"xop: rule '{rule_id}' not found in conduct/", file=sys.stderr)
            sys.exit(EXIT_ERROR)
    else:
        rule_files = sorted(
            f for f in conduct_dir.glob("*.md") if not f.name.startswith("_")
        )

    fixtures_dir = conduct_dir / "fixtures"
    total_passed = total_failed = 0
    missing = []

    for rule_path in rule_files:
        rid = _parse_rule_id(rule_path)
        hold_path = fixtures_dir / f"{rid}.hold.json"
        drop_path = fixtures_dir / f"{rid}.drop.json"

        if not hold_path.exists() or not drop_path.exists():
            print(f"\n  [{rid}] MISSING fixtures — need both {rid}.hold.json and {rid}.drop.json",
                  file=sys.stderr)
            missing.append(rid)
            continue

        print(f"\n{'='*50}")
        print(f"  {rid} (conduct rule)")
        print(f"{'='*50}")

        # Pair lint before judgment
        lint_errors = _lint_pair(hold_path, drop_path)
        if lint_errors:
            for e in lint_errors:
                print(f"  LINT FAIL: {e}")
            total_failed += 2
            print(f"  hold [FAIL]  drop [FAIL]  (pair lint failed — fix before judgment)")
            continue

        hold_ok = _run_conduct_fixture(hold_path)
        drop_ok = _run_conduct_fixture(drop_path)
        hold_label = "ok" if hold_ok else "FAIL"
        drop_label = "ok" if drop_ok else "FAIL"
        print(f"  hold [{hold_label}]  drop [{drop_label}]")
        total_passed += (1 if hold_ok else 0) + (1 if drop_ok else 0)
        total_failed += (0 if hold_ok else 1) + (0 if drop_ok else 1)

    return total_passed, total_failed, missing


def _run_conduct_fixture(fixture_path: Path) -> bool:
    """Oracle stub: trigger_present_at_final → warranted/inherited. Returns True if pass."""
    fixture = json.loads(fixture_path.read_text())

    trigger_present = fixture.get("trigger_present_at_final")
    if trigger_present is None:
        print(f"    {fixture_path.name}: FAIL — missing trigger_present_at_final")
        return False

    oracle = "warranted" if trigger_present else "inherited"
    gold = fixture.get("gold")

    if oracle != gold:
        print(f"    {fixture_path.name}: FAIL — oracle='{oracle}' gold='{gold}'")
        return False

    return True


def _print_conduct_summary(passed: int, failed: int, missing: list):
    print(f"\n{'='*50}")
    print(f"  TOTAL: {passed}/{passed + failed} passed")
    print(f"{'='*50}")
    print("\n[Note: rule judgment is oracle-stubbed — swap for a validated judge after the blind-label pilot.]")
    if missing:
        print(f"\nFAIL: {len(missing)} rule(s) had no fixtures: {', '.join(missing)}.", file=sys.stderr)
        sys.exit(1)
    if passed == 0 and failed == 0:
        print("\nFAIL: zero fixtures ran.", file=sys.stderr)
        sys.exit(1)


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
# Conduct Kit commands
# ---------------------------------------------------------------------------
def _detect_harness(agent_dir: Path) -> str:
    if (agent_dir / "agent.ts").exists() and (agent_dir / "instructions.md").exists():
        return "eve"
    if (agent_dir / ".claude").exists():
        return "claude-code"
    if (agent_dir / "langgraph.json").exists():
        return "langgraph"
    return "unknown"


def _write_run_yaml(path: Path, harness: str):
    lines = [
        f"harness: {harness}           # eve | claude-code | langgraph | none | unknown",
    ]
    if harness == "unknown":
        lines.append("# harness not detected — set manually to: eve | claude-code | langgraph | none")
    lines += [
        "# conduct is enforced by the release controller between \"output produced\"",
        "# and \"output delivered\", whatever the harness. adapters live in xop-kit.",
        "release_on:",
        "  - guards              # run conduct/guards.yaml",
        "  - judgment            # run rule adjudication on flags",
        "  # controller emits RELEASE / RETRY / HOLD / HALT",
        "",
    ]
    path.write_text("\n".join(lines))


def cmd_init(args):
    import shutil
    name = args.name
    target = Path(name)

    if target.exists():
        print(f"xop: '{name}' already exists. Remove it or choose a different name.", file=sys.stderr)
        sys.exit(EXIT_ERROR)

    template_dir = FRAMEWORK_ROOT / "template"
    if not template_dir.exists():
        print(f"xop: template directory not found at {template_dir}", file=sys.stderr)
        sys.exit(EXIT_ERROR)

    shutil.copytree(template_dir, target)

    # Replace {{AGENT_NAME}} in agent.md
    agent_md = target / "agent.md"
    if agent_md.exists():
        agent_md.write_text(agent_md.read_text().replace("{{AGENT_NAME}}", name))

    # Create empty skills/ and tools/
    for d in ("skills", "tools"):
        (target / d).mkdir(exist_ok=True)
        (target / d / ".gitkeep").touch()

    _write_run_yaml(target / "run.yaml", "none")

    print(f"Scaffolded {name}/")
    print(f"  conduct/   — two starter rules + fixtures (done-means-verified, claims-need-receipts)")
    print(f"  skills/    — empty, ready for your playbooks")
    print(f"  tools/     — empty, ready for your tool bindings")
    print(f"  run.yaml   — harness: none (set when you choose a harness)")
    print(f"\nNext:")
    print(f"  cd {name}")
    print(f"  xop test        # verify the scaffold is green")
    print(f"  xop add-rule    # add your own conduct rules")


def cmd_wrap(args):
    import shutil
    agent_dir = Path(args.path).resolve()

    if not agent_dir.exists():
        print(f"xop: path not found: {args.path}", file=sys.stderr)
        sys.exit(EXIT_ERROR)

    conduct_dir = agent_dir / "conduct"
    if conduct_dir.exists():
        print(f"xop: conduct/ already exists in {args.path}. Use 'xop add-rule' to extend it.",
              file=sys.stderr)
        sys.exit(EXIT_ERROR)

    template_conduct = FRAMEWORK_ROOT / "template" / "conduct"
    if not template_conduct.exists():
        print(f"xop: template/conduct not found at {template_conduct}", file=sys.stderr)
        sys.exit(EXIT_ERROR)

    shutil.copytree(template_conduct, conduct_dir)

    harness = _detect_harness(agent_dir)
    run_yaml = agent_dir / "run.yaml"
    _write_run_yaml(run_yaml, harness)

    added_files = [
        "conduct/_gate.yaml",
        "conduct/guards.yaml",
        "conduct/done-means-verified.md",
        "conduct/claims-need-receipts.md",
        "conduct/fixtures/done-means-verified.hold.json",
        "conduct/fixtures/done-means-verified.drop.json",
        "conduct/fixtures/claims-need-receipts.hold.json",
        "conduct/fixtures/claims-need-receipts.drop.json",
        "run.yaml",
    ]

    # Write manifest — the proof that wrap was non-destructive
    manifest_path = conduct_dir / ".wrap-manifest"
    manifest_path.write_text(
        "# xop wrap manifest — files added by this operation\n"
        "# xop unwrap would remove exactly these files and nothing else.\n"
        + "\n".join(added_files) + "\n"
    )
    added_files.append("conduct/.wrap-manifest")

    untouched = sorted(
        f.name for f in agent_dir.iterdir()
        if f.name not in ("conduct", "run.yaml")
    )

    print(f"Wrapped {args.path}/")
    print("\nAdded:")
    for f in added_files:
        print(f"  + {f}")
    if harness == "unknown":
        print(f"    (harness not detected — set manually in run.yaml)")
    print(f"\nLeft untouched: {', '.join(untouched) if untouched else '(none)'}")
    print(f"\nNext: cd {args.path} && xop test")


def cmd_add_rule(args):
    conduct_dir = Path.cwd() / "conduct"
    if not conduct_dir.exists():
        print("xop: no conduct/ directory found. Run from inside an agent directory, "
              "or run 'xop init' first.", file=sys.stderr)
        sys.exit(EXIT_ERROR)

    print("xop add-rule — fixtures first.")
    print("You need a hold case AND a drop case before you've found the rule.")
    print("Both are required. If you can't produce both, Ctrl-C now.\n")

    rule_id = input("id (slug, e.g. no-empty-promises): ").strip()
    if not rule_id:
        print("xop: id is required.", file=sys.stderr)
        sys.exit(EXIT_ERROR)

    rule_path = conduct_dir / f"{rule_id}.md"
    if rule_path.exists():
        print(f"xop: rule '{rule_id}' already exists.", file=sys.stderr)
        sys.exit(EXIT_ERROR)

    # ── HOLD CASE ────────────────────────────────────────────────────────────
    print("\n── HOLD CASE ──────────────────────────────────────────────────────")
    print("The situation where the rule MUST hold: trigger is present, agent holds correctly.")
    print("Enter turns (blank role to finish). Last turn must be assistant.\n")

    hold_turns = []
    while True:
        role = input(f"  turn {len(hold_turns)+1} role (user/assistant, blank to stop): ").strip().lower()
        if not role:
            break
        if role not in ("user", "assistant"):
            print("  role must be 'user' or 'assistant'")
            continue
        content = input(f"  turn {len(hold_turns)+1} content: ").strip()
        hold_turns.append({"role": role, "content": content})

    if len(hold_turns) < 2:
        print("\nxop: hold case needs at least 2 turns. Can't write the rule without it.", file=sys.stderr)
        sys.exit(EXIT_ERROR)
    if hold_turns[-1]["role"] != "assistant":
        print("\nxop: last turn must be the assistant's response (the held stance).", file=sys.stderr)
        sys.exit(EXIT_ERROR)
    if hold_turns[-2]["role"] != "user":
        print("\nxop: second-to-last turn must be the user's message (the pressure/trigger).", file=sys.stderr)
        sys.exit(EXIT_ERROR)

    hold_trigger = input("\nTriggering condition (one sentence — what makes the warrant present): ").strip()
    if not hold_trigger:
        print("xop: triggering condition is required.", file=sys.stderr)
        sys.exit(EXIT_ERROR)

    # ── DROP CASE ────────────────────────────────────────────────────────────
    print("\n── DROP CASE ──────────────────────────────────────────────────────")
    print("Same prefix, same final assistant turn — only the final user turn changes.")
    print(f"Current final user turn: \"{hold_turns[-2]['content']}\"")
    print("What does the user say that clears the warrant? (the artifact, source, confirmation)\n")

    drop_final_user = input("Drop final user turn content: ").strip()
    if not drop_final_user:
        print("\nxop: drop case required. Can't write the rule without both cases.", file=sys.stderr)
        sys.exit(EXIT_ERROR)
    if drop_final_user == hold_turns[-2]["content"]:
        print("\nxop: drop final user turn must differ from hold.", file=sys.stderr)
        sys.exit(EXIT_ERROR)

    drop_turns = hold_turns[:-2] + [{"role": "user", "content": drop_final_user}] + [hold_turns[-1]]

    # ── RULE FIELDS ──────────────────────────────────────────────────────────
    print("\n── RULE FIELDS ────────────────────────────────────────────────────")
    print("Both cases in hand. Now define the rule.\n")

    applies_when = input("applies-when (trigger condition): ").strip()
    change_when  = input("change-course-when (condition is gone): ").strip()
    when_unsure  = input("when-unsure (abstain behavior): ").strip()
    never_break  = input("never-break (the invariant): ").strip()

    if not all([applies_when, change_when, when_unsure, never_break]):
        print("xop: all four rule fields are required.", file=sys.stderr)
        sys.exit(EXIT_ERROR)

    # Write everything atomically
    title = rule_id.replace("-", " ").title()
    rule_path.write_text(
        f"---\n"
        f"id: {rule_id}\n"
        f"applies-when: {applies_when}\n"
        f"change-course-when: {change_when}\n"
        f"when-unsure: {when_unsure}\n"
        f"never-break: {never_break}\n"
        f"---\n\n"
        f"# {title}\n\n"
        f"[Describe the rule: what failure does it prevent, when is the caution warranted, when does it clear.]\n\n"
        f"**Warranted (hold):** [describe the hold condition]\n\n"
        f"**Inherited (drop):** [describe the drop condition]\n\n"
        f"Fixtures: `fixtures/{rule_id}.hold.json` · `fixtures/{rule_id}.drop.json`\n"
    )

    fixtures_dir = conduct_dir / "fixtures"
    fixtures_dir.mkdir(exist_ok=True)

    hold_fixture = {
        "rule": rule_id,
        "expect": "hold",
        "why": "Trigger is present; the agent must hold.",
        "turns": hold_turns,
        "triggering_condition": hold_trigger,
        "trigger_present_at_final": True,
        "gold": "warranted",
        "labeler_id": "AUTHOR_SEED",
        "blind": False,
    }
    drop_fixture = {
        "rule": rule_id,
        "expect": "drop",
        "why": "User's final message clears the trigger; persisting the hold is overhang.",
        "turns": drop_turns,
        "triggering_condition": hold_trigger,
        "trigger_present_at_final": False,
        "gold": "inherited",
        "labeler_id": "AUTHOR_SEED",
        "blind": False,
    }

    (fixtures_dir / f"{rule_id}.hold.json").write_text(json.dumps(hold_fixture, indent=2))
    (fixtures_dir / f"{rule_id}.drop.json").write_text(json.dumps(drop_fixture, indent=2))

    print(f"\nCreated:")
    print(f"  conduct/{rule_id}.md")
    print(f"  conduct/fixtures/{rule_id}.hold.json")
    print(f"  conduct/fixtures/{rule_id}.drop.json")
    print(f"\nRun: xop test --rule {rule_id}")


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
    p_test.add_argument("--rule", help="Test a specific conduct rule (from conduct/ in cwd)")

    # list
    p_list = sub.add_parser("list", help="List registered Work Packs")
    p_list.add_argument("--json", action="store_true", dest="json", help="JSON output")

    # info
    p_info = sub.add_parser("info", help="Show Work Pack details")
    p_info.add_argument("pack", help="Work Pack name")

    # init
    p_init = sub.add_parser("init", help="Scaffold a new conduct-first agent")
    p_init.add_argument("name", help="Agent name (creates ./<name>/)")

    # wrap
    p_wrap = sub.add_parser("wrap", help="Add a conduct layer to an existing agent")
    p_wrap.add_argument("path", help="Path to the agent directory")

    # add-rule
    sub.add_parser("add-rule", help="Interactively author a new conduct rule")

    args = parser.parse_args()

    if args.command == "scan":
        cmd_scan(args)
    elif args.command == "test":
        cmd_test(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "info":
        cmd_info(args)
    elif args.command == "init":
        cmd_init(args)
    elif args.command == "wrap":
        cmd_wrap(args)
    elif args.command == "add-rule":
        cmd_add_rule(args)
    else:
        parser.print_help()
        sys.exit(EXIT_ERROR)


if __name__ == "__main__":
    main()
