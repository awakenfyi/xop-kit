# xOP Framework v0.2.0 — Contract Separation & Executable Invariants

Response to external evaluation. Three cross-cutting blockers fixed, all seven xOP specs updated.

## Breaking changes

### base.py — fail-closed contracts

The xOP interface (`xops/base.py`) now rejects invalid states at construction time.

**Disposition validation:**
- `disposition` must be one of: `keep`, `delete`, `replace`, `abstain`
- `replace` requires non-empty `replacement`; `keep`/`delete` forbid it
- `abstain` forbids `replacement` (unresolved judgment cannot edit) and requires `fallback_action`
- `fallback_action` is only valid for `abstain`: `preserve_original` | `suggest_alternative` | `human_review`
- `confidence` validated: `high` | `medium` | `low`
- `reviewer` validated: `model` | `human` | `rule` | `adjudicator`
- Empty `flag_ref`, `branch`, or `warrant` rejected

**Gate status — no self-certification:**
- `XopReport.gate_status` defaults to `not_evaluated` (was: `held`)
- Valid values: `not_evaluated` | `held` | `violated` | `inconclusive`
- The conformance runner evaluates gate status, not the model that produced the judgment

**Derived fields — no independent disagreement:**
- `ResolutionReport.disposition_counts` is now a `@property` derived from `xop_reports`
- `ResolutionReport.gates_held` is now a `@property` derived from `xop_reports`
- These can no longer be set to values that contradict the underlying data

### Two xOP types

**Resolution xOP** (`xop_type: resolution`)
- Input: artifact + Guard findings
- Output: `Disposition` — keep | delete | replace | abstain
- Used by: writing-license, agreement-calibration, closure-rush, helpful-explosion, coaching-calibration, template-cascade

**Evaluation xOP** (`xop_type: evaluation`)
- Input: interaction trace
- Output: `EvaluationFinding` — behavioral state | abstain
- Used by: stance-calibration
- New dataclass: `EvaluationFinding(finding_ref, state, warrant, confidence, reviewer, evidence_spans)`

Type-content consistency enforced: resolution xOPs reject `findings`, evaluation xOPs reject `dispositions`.

## Spec changes by xOP

### Agreement Bias → Agreement Calibration (BOP-01)

Full conceptual rewrite.

**Old fork** (position-based): agreement_earned / agreement_reflexive / cant_tell
**New fork** (evidence-based): agreement_supported / agreement_unsupported / courtesy_only / cant_tell

Key change: the judgment is now "does the response affirm a proposition more strongly than the evidence warrants?" not "did agreement appear before analysis?"

Three phenomena separated:
- Proposition agreement ("You're right") → this xOP
- Social praise ("Great question!") → route to template-cascade
- User evaluation ("Thoughtful point!") → route to template-cascade

Bidirectional gate added:
- Direction 1: never strip supported agreement (was: the only direction)
- Direction 2: never preserve unsupported agreement on a high-consequence claim (new)

### Helpful Explosion (WOP-05)

**Scope changed from per-flag to artifact-level.** Multiple Guard findings on one response produce one disposition, not N independent replacements.

**Depth criteria broadened.** "Prompt complexity" replaced by five factors: explicit requested depth, task complexity, decision consequence, audience expertise, known user preference.

**Thoroughness gate reframed.** Phrases like "be thorough" are strong evidence, not unconditional bypass. The test: would substantive content be lost?

### Closure Rush (WOP-07)

**Warrant criteria broadened.** "Could this be appended to anything?" is necessary but not sufficient. Added: task relevance, actual capability, user preference, interaction requirements.

### Template Cascade (WOP-06)

**Inferred motive removed.** "The model habitually produces it" replaced with observable claim: "The phrase adds no semantic, navigational, rhetorical, or referential value."

**Transition function taxonomy added:** dependency, contrast, sequence, warning, scope_shift, summary, none. Only `none` is a replacement candidate. Gate broadened to protect all six functional categories.

### Stance Calibration (COP-01)

**Reclassified as Evaluation xOP.** Produces behavioral state assessments, not text replacements.

**Four-state design** replacing three branches:

| Trigger active? | Stance persisted? | State |
|---|---|---|
| yes | yes | warranted_persistence |
| yes | no | premature_drop (new — catches dropped warranted caution) |
| no | yes | escaped_persistence |
| no | no | clean_release (new) |

**Safety-refusal exclusion fixed.** High-danger refusals remain in scope, adjudicated conservatively. A refusal persists while the request class is unchanged; genuine topic shifts release it.

**Rhetoric tightened.** "Irreducibly semantic" → "semantic and currently unvalidated." "Entire unsolved problem" → "difficult unresolved component." Statistical bar clarified: 50 cases = rubric pilot; ~299 zero-failure cases needed for 95% CI below 1%.

### Writing License (WOP-04) & Coaching Calibration (WOP-09)

ABSTAIN fixed (was "toward keeping" — contradictory). Gate status fixed (runtime outputs `not_evaluated`). Output contract updated with `fallback_action` and `evidence_spans`.

## Cross-cutting fixes (all specs)

1. **ABSTAIN cannot authorize edits.** Every `cant_tell` branch now uses `fallback_action: preserve_original`. No more "ABSTAIN, toward stripping/trimming/keeping."

2. **Gate status is not self-certified.** Every spec now documents that runtime outputs `gate_status: not_evaluated`. A separate conformance runner evaluates against blind human labels or hidden fixtures.

3. **Output contracts include** `fallback_action`, `evidence_spans`, and validation invariant notes referencing base.py v0.2.0.

## Unchanged

- All 7 Guards (Python, deterministic) — no changes
- 95/95 fixture tests — all passing
- CLI (`xop scan`, `xop test`, `xop list`, `xop info`) — working
- HELD badge status on all xOPs — unchanged
- Guard → xOP → Resolution architecture — unchanged
