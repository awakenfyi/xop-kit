# [ID]-[name] · [BADGE]

> family: [WOP/COP/...] · anchor: [what triggers this xOP]
> optimizes-for: [what it protects] · never-optimizes-for: [what it explicitly avoids]

## Metadata

```yaml
xop_type: resolution | evaluation
scope: flag | artifact | conversation
required_context:
  - user_prompt
  - artifact
  - guard_findings
on_abstain:
  action: preserve_original
  route: human_review
judge_failure:
  action: stop
  result: judge_error
gate:
  runtime_status: not_evaluated
  evaluation_method: blind_human_labels
evidence_requirements:
  - exact source spans
  - guard and xOP versions
  - input hash
```

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

For artifact-level xOPs, multiple flags are grouped:

```json
{
  "scope": "artifact",
  "finding_refs": ["...", "..."],
  "artifact_text": "...",
  "user_prompt": "..."
}
```

## Residual

The residual describes the gap between expected and actual behavior.
It is explanatory language, not a numerical operand.

- **x̂ (expected)** — [What the correct/intended behavior looks like]
- **x (actual)** — [What the problematic behavior looks like]
- **L = x − x̂** — [The gap. Describes the condition to be resolved.]

Condition states:
- **condition present** — the gap is observable and clearly present
- **condition absent** — the behavior matches expectations; no gap
- **condition unknown** — cannot determine from available evidence

## Fork — the branches

### [branch_1_name]
[Condition] → **KEEP** / **REPLACE** / **DELETE**. [Details.]
→ Confidence: high.

### [branch_2_name]
[Condition] → **KEEP** / **REPLACE** / **DELETE**. [Details.]
→ Provide replacement text in the disposition (REPLACE only).
→ Confidence: high.

### cant_tell
[Condition where judgment is genuinely unresolved.]
→ **ABSTAIN.**
→ `fallback_action: preserve_original` — an unresolved judgment never silently changes the author's text.
→ Confidence: low.
→ Note the ambiguity in the warrant field.

**ABSTAIN rules:**
- ABSTAIN means the judgment was unresolved. It CANNOT authorize a modification.
- ABSTAIN does not mean "edit toward X." That is a resolved judgment with low confidence, not an abstention.
- The tool may show a suggested alternative, but it MUST NOT apply it automatically.
- Use `fallback_action` to specify what happens with the unresolved judgment:
  - `preserve_original` — leave the text unchanged (safest default for writing)
  - `suggest_alternative` — show a suggestion but do not apply it
  - `human_review` — route to human review queue

## Output contract

For Resolution xOPs — each flag gets a disposition:
```json
{
  "flag_ref": "...",
  "disposition": "keep | delete | replace | abstain",
  "branch": "...",
  "warrant": "...",
  "confidence": "high | medium | low",
  "replacement": "",
  "fallback_action": "",
  "reviewer": "model",
  "evidence_spans": []
}
```

For artifact-level Resolution xOPs:
```json
{
  "scope": "artifact",
  "finding_refs": ["...", "..."],
  "disposition": "replace",
  "branch": "...",
  "warrant": "...",
  "confidence": "high",
  "replacement": "[full rewritten artifact text]",
  "reviewer": "model"
}
```

For Evaluation xOPs — findings, not dispositions:
```json
{
  "finding_ref": "...",
  "state": "[domain-specific behavioral state]",
  "warrant": "...",
  "confidence": "high | medium | low",
  "reviewer": "model",
  "evidence_spans": []
}
```

**Validation invariants (enforced by base.py):**
- `replace` requires non-empty `replacement`
- `keep` and `delete` forbid `replacement`
- `abstain` forbids `replacement` and requires `fallback_action`
- Empty `flag_ref`, `branch`, or `warrant` are invalid
- Invalid enum values are rejected at construction

## Gate — the one invariant. Fixed law, not a recommendation.

[The rule that must never be violated.]

**Runtime gate status:**

The xOP CANNOT certify that its own gate held. During an ordinary run,
the correct output is:

```json
"gate_status": "not_evaluated"
```

A separate conformance runner may later evaluate:
- `held` — the gate invariant was satisfied
- `violated` — the gate invariant was broken
- `inconclusive` — could not determine

The evaluation method is blind human labels or hidden fixtures,
NOT the same model that produced the judgment.

## When-to-fail — the inversion

[This FAILS if...]

Report failure directions separately when the gate protects two directions:
- **Direction 1**: [dangerous content wrongly stripped/preserved]
- **Direction 2**: [safe content wrongly stripped/preserved]

## Drift — what to log

[Telemetry points]

## Badge

[Current badge + graduation path]

-- WELL-FORMED, NOT VALID --
Well-formed = correct shape, admission tests applied, trigger tracks warrant.
Valid = the gate measurably holds against blind human labels.
A HELD badge here means it operates as structural discipline, not a scored metric.
