# xOP Kit — Reference Implementation

[![status: alpha](https://img.shields.io/badge/status-alpha-orange)](https://github.com/awakenfyi/xop-kit)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![python: 3.8+](https://img.shields.io/badge/python-3.8%2B-blue)](setup.py)

The reference implementation of the [xOP Standard](https://github.com/awakenfyi/xop).

> **Read this first.** Seven Guards are deterministic and rule-tested (95/95 fixtures). That tests
> Guard determinism and rule coverage — NOT whether the gate holds. The central claim of the xOP
> Standard — `fp_on_warranted == 0` — has never been validated against blind human labels. The
> pilot has not run. This is an executor for a standard whose gate is still unproven. Ship it
> honest: **alpha**.

---

## What this is

xOP Kit executes the xOP Standard's quality-gate contract inside agent loops:

```
Input text / conversation
        │
        ├── Guard 1 (deterministic) ──► flag report
        ├── Guard 2 (deterministic) ──► flag report      ← parallel, zero token cost
        ├── Guard N (deterministic) ──► flag report
        │
        ▼
Orchestrator (merges reports)
        │
        ├── xOP 1 (judgment) ──► disposition             ← scoped to flagged content only
        ├── xOP 2 (judgment) ──► disposition             ← parallel where independent
        │
        ▼
Release control  →  RELEASE / RETRY / HOLD / HALT
```

The Kit implements the four-layer architecture defined in the Standard. See
[awakenfyi/xop](https://github.com/awakenfyi/xop) for the contract, specification, and catalog.

---

## Core concepts

**Guard** — A deterministic scanner. No model, no judgment. Input: text. Output: JSON flag report.
PASS / REVIEW / FAIL. A Guard that requires judgment is not a Guard — it's a misclassified xOP.

**xOP** — A judgment engine. Receives a Guard's finding plus context. Returns a disposition:
`keep | replace | delete | abstain`. An xOP without a gate is not an xOP — it's a suggestion.

**The gate** — `fp_on_warranted == 0`. Never suppress a state that is still warranted. The one
rule that does not move.

**Work Pack** — The distribution unit: Guard + xOP spec + fixtures. One folder, one domain.

---

## Interfaces

### Guard output (JSON)
```json
{
  "guard_id": "no-ai-tells",
  "version": "0.2.0",
  "verdict": "REVIEW",
  "flags": [
    {
      "rule_id": "vocabulary.delve",
      "tier": "vocabulary",
      "severity": "review",
      "match": "delve",
      "line": 12,
      "context": "The geologists delve below the fault line."
    }
  ],
  "metadata": { "input_words": 450, "scan_ms": 12 }
}
```

### xOP disposition output (JSON)
```json
{
  "xop_id": "writing-license",
  "version": "0.2.0",
  "dispositions": [
    {
      "flag_ref": "vocabulary.delve@L12",
      "disposition": "keep",
      "warrant": "Literal geological usage — the word means physical digging here",
      "confidence": "high",
      "branch": "warrant_present"
    }
  ],
  "gate_status": "not_evaluated",
  "gate_violations": []
}
```

---

## File structure

```
xop-kit/
├── README.md
├── LICENSE
├── setup.py
├── registry.json              # registered Work Packs
├── cli.py                     # xop scan / test / list / info
├── orchestrator.py            # Guards → xOPs → Resolution
├── guards/
│   ├── base.py                # Guard interface + runner
│   ├── no_ai_tells.py         # writing domain
│   ├── agreement_bias.py
│   ├── closure_rush.py
│   ├── helpful_explosion.py
│   ├── coaching.py
│   ├── template_cascade.py
│   └── stance_calibration.py  # evaluation xOP (needs conversation input)
├── xops/
│   ├── base.py                # xOP interface + fail-closed contracts
│   ├── _TEMPLATE.md
│   ├── writing_license.md
│   ├── agreement_bias.md
│   ├── closure_rush.md
│   ├── helpful_explosion.md
│   ├── coaching.md
│   ├── template_cascade.md
│   └── stance_calibration.md
├── agents/
│   ├── guard_agent.md
│   ├── xop_agent.md
│   └── orchestrator_agent.md
└── tests/
    └── fixtures/              # 95 fixtures across 7 Guards
```

---

## Usage

### CLI
```bash
# Scan a file against all Guards
xop scan draft.md

# Scan with a specific Work Pack
xop scan draft.md --pack writing

# Run all fixture tests
xop test

# List registered Work Packs
xop list

# Show Work Pack details + xOP spec
xop info writing
```

### Install (local)
```bash
pip install -e .
```

### Python API
```python
from guards.agreement_bias import AgreementBiasGuard

guard = AgreementBiasGuard()
report = guard.run(text)
print(report.verdict)   # PASS | REVIEW | FAIL
print(report.to_json())
```

### Self-check loop
```python
from orchestrator import Pipeline

pipe = Pipeline()
reports = pipe.run_all_guards(text)
# Guards run; xOP judgment requires an LLM agent — see agents/orchestrator_agent.md
```

---

## Work Packs (Wave 1)

| Pack | Guard | Shadow pattern | xOP type |
|------|-------|---------------|----------|
| `writing` | no-ai-tells | — | resolution |
| `agreement` | agreement-bias | S-01 | resolution |
| `closure` | closure-rush | S-07 | resolution |
| `helpful` | helpful-explosion | S-02 | resolution (artifact scope) |
| `coaching` | coaching-calibration | S-04 | resolution |
| `template` | template-cascade | S-03 | resolution |
| `stance` | stance-calibration | — | evaluation (conversation scope) |

All seven Guards: 95/95 fixtures passing. Determinism and rule coverage confirmed.
Gate validation against blind human labels: **not yet run**.

---

## Adding a Work Pack

1. Write the Guard (`guards/<name>.py`, deterministic, extends `guards/base.Guard`)
2. Write the xOP spec (`xops/<name>.md`, follows `xops/_TEMPLATE.md`)
3. Write fixtures (`tests/fixtures/<name>_fixtures.jsonl`, one per rule minimum)
4. Register in `registry.json`
5. `xop test --pack <name>` → must pass before merge

---

## What this is not

- **Not a validated detector.** The Guards are deterministic and rule-tested. The xOP judgment is
  fail-closed by contract. Neither has been validated against independent human labels.
- **Not the xOP Standard.** The Standard (contract, specification, catalog) lives at
  [awakenfyi/xop](https://github.com/awakenfyi/xop). This repo implements it.
- **Not production-ready.** Alpha. The gate claim requires the pilot to run first.

---

*Lyra Labs · [awakenfyi/xop](https://github.com/awakenfyi/xop) · Built to be wrongable.*
