# [ID]-[name] · [BADGE]

> family: [WOP/COP/...] · anchor: [what triggers this xOP]
> optimizes-for: [what it protects] · never-optimizes-for: [what it explicitly avoids]

## Admission — run BOTH before engaging.

- **Test 1 · judgment-bearing?** [YES/NO]. [Why.]
- **Test 2 · observable x?** [YES/NO]. [What's observable in the input.]

If either test is NO, this is a Guard, not an xOP.

## Purpose

[One paragraph. What this xOP prevents or protects.]

## Use when

[When to apply this xOP.]

## Do not use → handoff

[When to hand off to a different tool or process.]

## Input contract

This xOP receives flag reports from Guard: `[guard_id]`

```json
{
  "flag_ref": "...",
  "match": "...",
  "context": "...",
  "severity": "review"
}
```

## Residual

- **x̂ (expected)** — [What the correct/intended behavior looks like]
- **x (actual)** — [What the problematic behavior looks like]
- **L = x − x̂** — [The gap that triggers the fork]

## Fork — the branches

### [branch_1_name]
[Condition] → [KEEP/REPLACE/ABSTAIN]. [Details.]

### [branch_2_name]
[Condition] → [KEEP/REPLACE/ABSTAIN]. [Details.]

### [branch_3_name] (if needed)
[Condition] → [KEEP/REPLACE/ABSTAIN]. [Details.]

## Output contract

```json
{
  "flag_ref": "...",
  "disposition": "...",
  "branch": "...",
  "warrant": "...",
  "confidence": "...",
  "replacement": "",
  "reviewer": "model"
}
```

## Gate — the one invariant.

[The rule that must never be violated. Not a recommendation — a law.]

- **gate_status: held** — [what "held" means]
- **gate_status: violated** — [what violation looks like]

## When-to-fail — the inversion

[This FAILS if...]

## Drift — what to log

[Telemetry points]

## Badge

[Current badge + graduation path]
