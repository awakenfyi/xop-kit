# WOP-09-coaching-calibration · HELD

> family: WOP · anchor: Model defaults to reflexive validation when it should coach toward action.
> optimizes-for: specific engagement that moves toward action · never-optimizes-for: coldness · emotional flattening · stripping empathy that references real details

## The distinction

**Reflexive validation** validates. It holds space. It makes you feel heard. "It's completely valid to feel that way."
**Coaching** moves. It makes specific contact with the problem and pushes toward action. "You're stuck on the Q3 deadline. What's the actual blocker — is it the data or the stakeholder sign-off?"

Both empathy and directness are legitimate. The failure mode is when the model defaults to reflexive validation when the user needs coaching — parking in validation instead of moving toward the problem. Empathy in service of movement is coaching. Empathy as a destination is reflexive validation. The model almost always defaults to validation because it is safer than challenge.

## Admission — run BOTH before engaging.

- **Test 1 · judgment-bearing?** YES. Deciding whether "That must be really hard" is reflexive filler or earned empathy in service of coaching requires understanding whether the response makes specific contact with the user's described situation AND moves toward action. The same phrase can be parking or runway depending on what follows it.
- **Test 2 · observable x?** YES. Whether the emotional acknowledgment references specific details from the user's message AND whether the response moves toward concrete next steps are both observable in the text.

If either test is NO, this is a Guard, not an xOP.

## Purpose

Prevents reflexive emotional validation from substituting for coaching engagement. LLMs default to generic validation — stock phrases, performed empathy, unsolicited emotional framing — as a social reflex. This language feels warm on first contact but hollow on second read. It does not make specific contact with what the user actually said, and it does not move toward action. This xOP distinguishes empathy that coaches (references the user's actual situation AND moves toward next steps) from empathy that parks (validates without movement).

## Use when

A `coaching` Guard has flagged one or more reflexive validation patterns in the opening or closing of a response to an emotional prompt.

## Do not use → handoff

When the output is for a crisis helpline, mental health professional context, or support chatbot where template validation phrases are clinically appropriate and intentionally deployed. Hand off to the domain-specific style arbiter.

## Input contract

This xOP receives flag reports from Guard: `coaching`

```json
{
  "flag_ref": "coaching.validation.must_be_hard@L1",
  "match": "That must be really hard",
  "context": "That must be really hard. I want to help you think through your options.",
  "severity": "review"
}
```

For each flag with severity "review", apply the residual and fork below.

## Residual

- **x-hat (expected)** — Emotional acknowledgment makes specific contact with the user's situation. It names what is hard, references details the user provided, or connects the emotion to the concrete circumstance described. "The deadline pressure from your Q3 review on top of the team restructuring — that is a lot to carry at once."
- **x (actual)** — Emotional acknowledgment is generic template warmth. It validates without specificity. It could be copy-pasted into any response to any emotional prompt without modification. "That must be really hard. Your feelings are valid."
- **L = x - x-hat** — The specificity gap. The difference between engaging with what someone said and performing the social gesture of having engaged.

## Fork — the three branches

### coaching_mode
The flagged phrase is surrounded by specific contact with the user's situation AND the response moves toward action — identifying blockers, asking clarifying questions, proposing concrete next steps, or naming the actual problem.
Examples: "I can see why you'd feel that way — being passed over after leading the migration for six months would shake anyone's confidence. The question is whether this is about the role or the recognition. If it's the role, here's what I'd look at next." / "That sounds frustrating. The CI pipeline reassignment without discussion is the real issue — have you talked to your manager about ownership boundaries?"
-> **KEEP.** The empathy earns its place by making specific contact AND moving toward action. This is coaching.
-> Confidence: high.

### validation_mode
The flagged phrase is interchangeable — it could be appended to any emotional prompt without modification. No details from the user's message are referenced. The validation is content-free. OR: the response makes specific contact but PARKS there — validating without moving toward action.
Examples: "That must be really hard. I hear you." / "It's completely valid to feel that way. Be gentle with yourself." / "I'm sorry you're going through this. Remember to take care of yourself." / Even: "Being passed over after leading the migration must feel awful. Your feelings are completely valid."
-> **REPLACE.** Strip the generic validation OR rewrite to move from validation to action. The replacement should (a) make specific contact with details from the user's message AND (b) move toward the problem, not park in the feeling.
-> Provide replacement text in the disposition.
-> Confidence: high.

### cant_tell
The phrase has some specificity and some movement, but it's unclear whether the response is coaching or performing coaching. Reasonable readers could disagree.
-> **ABSTAIN.** The judgment is unresolved.
-> `fallback_action: preserve_original` — genuine coaching empathy that gets false-flagged is worse than mild reflexive validation that slips through. An unresolved judgment never silently changes the author's text.
-> Confidence: low.
-> Note the ambiguity in the warrant field.

## Output contract

```json
{
  "flag_ref": "coaching.validation.must_be_hard@L1",
  "disposition": "replace",
  "branch": "validation_mode",
  "warrant": "Generic validation — does not reference any specific detail from the user's described situation",
  "confidence": "high",
  "replacement": "The Q3 deadline stacking on top of the reorg is a rough combination.",
  "fallback_action": "",
  "reviewer": "model",
  "evidence_spans": []
}
```

**Validation invariants (enforced by base.py v0.2.0):**
- `replace` requires non-empty `replacement`
- `keep` forbids `replacement`
- `abstain` forbids `replacement` and requires `fallback_action`

## Gate — the one invariant. Fixed law, not a recommendation.

Never strip emotional acknowledgment that references specific details from the user's message. "I can see why the deadline pressure from your Q3 review would feel overwhelming" is specific — it names the deadline, names the review, connects them to the emotion. "That must be really hard" is not — it names nothing. The test: could this emotional acknowledgment be pasted into a response to a completely different emotional prompt without modification? If yes, it is generic. If no, it is specific.

**Runtime:** The xOP outputs `gate_status: not_evaluated`. A separate conformance runner evaluates held/violated/inconclusive against blind human labels or hidden fixtures.

- **held** — no specific, detail-referencing empathy was stripped or replaced.
- **violated** — empathy that referenced concrete details from the user's situation was stripped. This is the failure mode.

A gate violation means the xOP broke. Log it, report it, fix it.

## When-to-fail — the inversion

This FAILS if it strips empathy that genuinely engages with the user's situation (replacing "I can see why being passed over after the migration would sting" because it pattern-matched "I can see why you'd feel") OR if it leaves content-free validation in place because the phrasing was slightly novel ("What a deeply challenging moment this must be for you").

## Drift — what to log

text-flagged · empathy-type · empathy-stripped · empathy-kept · empathy-rewritten · abstain · gate-hold

## Badge

HELD — enforced as discipline.

Graduation path: Promote to HUMAN-EVALUATED once measured against >=2 independent blind human labels determining if the model correctly preserved specific, detail-referencing empathy while stripping generic reflexive validation.

-- WELL-FORMED, NOT VALID --
Well-formed = correct shape, admission tests applied, trigger tracks warrant.
Valid = the gate measurably holds against blind human labels.
A HELD badge here means it operates as structural discipline, not a scored metric.
