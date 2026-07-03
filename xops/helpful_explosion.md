# WOP-05-helpful-explosion · HELD

> family: WOP · anchor: A response whose structural bulk exceeds what the prompt complexity warranted.
> optimizes-for: concision that matches prompt complexity · never-optimizes-for: terseness for its own sake · withholding useful detail · punishing thoroughness when asked for it

## Admission — run BOTH before engaging.

- **Test 1 · judgment-bearing?** YES. A ten-bullet list answering "what are the main benefits of X?" may be proportionate. The same list answering "is X better than Y?" is reflexive over-helping. Distinguishing the two requires reading the prompt, not counting bullets.
- **Test 2 · observable x?** YES. The prompt complexity, the structural shape of the response (bullet count, header count, word count), and any explicit user requests for thoroughness are all observable in the input pair.

If either test is NO, this is a Guard, not an xOP.

## Purpose

Prevents the "helpful explosion" — the pattern where a model reflexively generates exhaustive lists, walls of text, and excessive structure regardless of what was asked. The failure mode is not length itself but disproportionate length: a simple yes/no question answered with ten bullet points and four sub-headers.

## Use when

A structural Guard (`helpful-explosion`) has flagged a response for excessive bullets, headers, numbered lists, enumeration openers, or advisory word count. The flag means the structure looks heavy; this xOP decides whether the weight is warranted.

## Do not use → handoff

When the user explicitly requested a comprehensive, exhaustive, or detailed response ("give me everything you know," "be thorough," "full list," "all the options"). In those cases the Gate below prevents trimming regardless, but if the prompt is unambiguously asking for exhaustiveness, skip the xOP entirely — there is nothing to judge.

## Input contract

This xOP receives flag reports from Guard: `helpful-explosion`

```json
{
  "flag_ref": "structure.excessive_bullets@L14",
  "match": "12 bullet items (threshold: 7)",
  "context": "Response contains 12 bullet points",
  "severity": "review",
  "advisory": {
    "word_count": 943,
    "bullet_count": 12,
    "header_count": 3,
    "word_count_exceeds_advisory": true
  }
}
```

For each flag with severity "review", consider the full prompt + response pair and apply the residual and fork below.

## Residual

- **x-hat (expected)** — Response length and structure match prompt complexity. A simple question gets a direct answer. A complex question gets appropriate depth. The response earns its length.
- **x (actual)** — Response is structurally exhaustive regardless of what was asked. Ten tips when two would do. Four sub-headers for a single-concept answer. An enumeration opener ("Here are 12 ways...") when the user asked a binary question.
- **L = x - x-hat** — The structural surplus: the bullets, headers, and words that exist because the model defaults to exhaustiveness, not because the prompt demanded them.

## Fork — the three branches

### length_warranted
The prompt is complex, multi-part, or explicitly asks for depth. The structural weight is proportionate to what was asked.
-> **KEEP.** Do not trim. The response earned its length.
-> Confidence: high.

### length_reflexive
The prompt is simple, narrow, or asks a direct question. The response explodes into lists, sub-sections, or enumeration patterns that the prompt did not request.
-> **REPLACE.** Trim to what was actually asked. Collapse bullet lists into prose where appropriate. Remove unnecessary headers. Cut the enumeration opener and deliver the answer directly.
-> Provide a trimmed version in the disposition.
-> Confidence: high.

### cant_tell
The prompt complexity is ambiguous — a question that could reasonably receive either a short or long answer.
-> **ABSTAIN, toward trimming.** Over-helping has lower cost than under-helping in most contexts, but the helpful-explosion pattern trains users to skim rather than read, which degrades trust over time. When in doubt, err toward concision.
-> Confidence: low.
-> Note the ambiguity in the warrant field.

## Output contract

```json
{
  "flag_ref": "structure.excessive_bullets@L14",
  "disposition": "replace",
  "branch": "length_reflexive",
  "warrant": "User asked 'what is X?' — a definitional question. 12 bullets with 4 headers is disproportionate. Trimmed to a 3-sentence definition.",
  "confidence": "high",
  "replacement": "[trimmed response text]",
  "reviewer": "model"
}
```

## Gate — the one invariant. Fixed law, not a recommendation.

Never trim a response where the user explicitly asked for comprehensiveness, thoroughness, or exhaustive detail. Phrases that activate the gate: "give me everything," "be thorough," "full list," "all the options," "comprehensive," "detailed breakdown," "don't leave anything out," "as much as you can."

- **gate_status: held** — no explicitly-requested comprehensive response was trimmed.
- **gate_status: violated** — a comprehensive response that the user asked for was trimmed. This is the failure mode.

A gate violation means the xOP broke. Log it, report it, fix it.

## When-to-fail — the inversion

This FAILS if it trims a response the user explicitly asked to be thorough, OR if it keeps a ten-bullet wall-of-text answer to "what time zone is Tokyo in?" because "more information is always better."

Both failure modes are real. The first destroys user trust ("I asked for detail and got less"). The second trains the user to stop reading ("every answer is a wall, so I skim everything").

## Drift — what to log

text-flagged · prompt-complexity-assessed · structure-warranted · structure-trimmed · abstain · gate-hold · gate-violation

## Badge

HELD — enforced as discipline.

Graduation path: Promote to HUMAN-EVALUATED once measured against >=20 blind human labels on prompt-response pairs, confirming that the model correctly trims reflexive explosions while preserving warranted depth. Key test: the "give me everything" gate must hold 100% of the time.

-- WELL-FORMED, NOT VALID --
Well-formed = correct shape, admission tests applied, trigger tracks warrant.
Valid = the gate measurably holds against blind human labels.
A HELD badge here means it operates as structural discipline, not a scored metric.
