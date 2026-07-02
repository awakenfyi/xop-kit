# WOP-04-writing-license · HELD

> family: WOP · anchor: The revision or generation of text containing flagged "AI tells."
> optimizes-for: authorial precision and voice · never-optimizes-for: detector evasion · homogenization · "smoothness"

## Admission — run BOTH before writing.

- **Test 1 · judgment-bearing?** YES. Deciding whether a word like "delve" is a literal, necessary choice (a geologist digging) or a lazy LLM metaphor (exploring a topic) requires semantic judgment.
- **Test 2 · observable x?** YES. The surrounding topic, subject matter, and literal definitions in the draft are observable in the text.

## Purpose

Prevents the flattening of legitimate authorial voice by distinguishing between a warranted, literal usage of a flagged word and lazy, generic LLM filler.

## Use when

Revising, editing, or generating prose where a deterministic Guard (like `no-ai-tells`) has flagged vocabulary or structural candidates for removal.

## Do not use → handoff

When generating strict legal, compliance, or regulatory boilerplate where specific boilerplate phrases (e.g., "In conclusion," "Rest assured") are legally mandated.

## Input contract

This xOP receives a Guard flag report (JSON) containing:
```json
{
  "flag_ref": "vocabulary.delve@L12",
  "match": "delve",
  "context": "The geologists delve below the fault line.",
  "severity": "review"
}
```

For each flag with severity "review", apply the residual and fork below.
Flags with severity "deny" are NOT sent to this xOP — they are house-style
hard failures handled by the Guard alone.

## Residual

- **x̂ (expected)** — The semantic context demands the flagged word or structure for literal precision (e.g., "delve" in mining, "tapestry" in weaving, "seamless" in tailoring).
- **x (actual)** — The word is being used as a generic transition, a lazy metaphor, or performative filler ("delve into the topic," "the rich tapestry of innovation," "seamless integration").
- **L = x − x̂** — The gap that triggers the fork.

## Fork — the three license branches

### warrant_present (literal/precise)
The word is used literally or with specific technical precision.
→ **KEEP.** Do not rewrite. Defend the author's word.
→ Confidence: high.

### warrant_absent (lazy/metaphorical)
The word is used as generic filler, a lazy metaphor, or performative transition.
→ **REPLACE.** Strip the tell. Rewrite using strong, active verbs and plain text.
→ Provide the replacement text in the disposition.
→ Confidence: high.

### cant_tell (ambiguous intent)
The intent is genuinely ambiguous — reasonable readers could disagree.
→ **ABSTAIN, toward keeping.** Better to leave a slight AI-tell than to accidentally destroy a writer's deliberate stylistic choice.
→ Confidence: low.
→ Note the ambiguity in the warrant field.

## Output contract

For each flag, return a disposition:
```json
{
  "flag_ref": "vocabulary.delve@L12",
  "disposition": "keep",
  "branch": "warrant_present",
  "warrant": "Literal geological usage — the word means physical digging here",
  "confidence": "high",
  "replacement": "",
  "reviewer": "model"
}
```

## Gate — the one invariant. Fixed law, not a recommendation.

Never override a warranted, precise authorial choice just because it appears on a blacklist.

- **gate_status: held** — no warranted words were replaced.
- **gate_status: violated** — a warranted word was replaced. This is the failure mode.

A gate violation means the xOP broke. Log it, report it, fix it.

## When-to-fail — the inversion

This FAILS if it blindly scrubs a valid word (removing "tapestry" from an essay about medieval art) OR if it justifies leaving lazy corporate metaphors in place because they sound "professional."

## Drift — what to log

text-flagged · warrant-checked · rewrite-released · abstain · gate-hold

## Badge

HELD — enforced as discipline.

Graduation path: Promote to HUMAN-EVALUATED once measured against ≥2 independent blind human labels determining if the model correctly preserved literal edge-cases (e.g., the "geologist" test) while scrubbing the slop.

── WELL-FORMED, NOT VALID ──
Well-formed = correct shape, admission tests applied, trigger tracks warrant.
Valid = the gate measurably holds against blind human labels.
A HELD badge here means it operates as structural discipline, not a scored metric.
