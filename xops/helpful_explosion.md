# WOP-05-helpful-explosion · HELD

> family: WOP · anchor: A response whose structural bulk exceeds what the warranted depth demanded.
> optimizes-for: concision that matches warranted depth · never-optimizes-for: terseness for its own sake · withholding useful detail · punishing thoroughness when asked for it

## Admission — run BOTH before engaging.

- **Test 1 · judgment-bearing?** YES. A ten-bullet list answering "what are the main benefits of X?" may be proportionate. The same list answering "is X better than Y?" is reflexive over-helping. Distinguishing the two requires reading the prompt, not counting bullets.
- **Test 2 · observable x?** YES. The warranted depth, the structural shape of the response (bullet count, header count, word count), and the depth cues in the prompt are all observable in the input pair.

If either test is NO, this is a Guard, not an xOP.

## Purpose

Prevents the "helpful explosion" — the pattern where a model reflexively generates exhaustive lists, walls of text, and excessive structure regardless of what was asked. The failure mode is not length itself but disproportionate length: a simple yes/no question answered with ten bullet points and four sub-headers.

## Use when

A structural Guard (`helpful-explosion`) has flagged a response for excessive bullets, headers, numbered lists, enumeration openers, or advisory word count. The flag means the structure looks heavy; this xOP decides whether the weight is warranted by evaluating the full artifact against the depth the prompt actually demanded.

## Do not use → handoff

When the flagged findings are clearly false positives — e.g., the user asked for a numbered list and got one. In those cases the findings should be dismissed at the Guard layer, not forwarded to this xOP.

## Scope

**Artifact-level.** A single response may trigger multiple Guard findings (excessive bullets, excessive headers, enumeration opener). This xOP evaluates them jointly against the full artifact. It does not produce one replacement per flag; it produces one disposition per artifact.

## Input contract

This xOP receives a batch of finding references from Guard: `helpful-explosion`, together with the full artifact text and the user prompt that produced it.

```json
{
  "scope": "artifact",
  "finding_refs": [
    "structure.excessive_bullets@L5",
    "structure.excessive_headers@L1"
  ],
  "artifact_text": "[full response text]",
  "user_prompt": "[original question]"
}
```

All referenced findings are evaluated together. The artifact text is the complete model response. The user prompt is the original input that produced it.

## Residual

- **x-hat (expected)** — Response length and structure match warranted depth. A simple question gets a direct answer. A complex question gets appropriate depth. The response earns its length.
- **x (actual)** — Response is structurally exhaustive regardless of what was asked. Ten tips when two would do. Four sub-headers for a single-concept answer. An enumeration opener ("Here are 12 ways...") when the user asked a binary question.
- **L = x - x-hat** — The structural surplus: the bullets, headers, and words that exist because the model defaults to exhaustiveness, not because the warranted depth demanded them.

### Warranted depth — what determines x-hat

"Prompt complexity" alone is too narrow. The warranted depth of a response depends on multiple factors, evaluated together:

1. **Explicit requested depth.** Did the user say "be thorough," "give me everything," "detailed breakdown"? This is strong evidence for depth — but not a blank check for irrelevant repetition. See the thoroughness gate below.
2. **Task complexity.** A multi-part question, a comparison across dimensions, or a request that requires covering several sub-topics warrants more structure than a single factual question.
3. **Decision consequence.** A short question about a high-stakes decision (medical, legal, financial, architectural) may warrant more depth than its syntactic simplicity suggests. "Should I take ibuprofen with this medication?" is five words but the answer should not be two.
4. **Audience expertise.** A question from a domain expert may warrant a denser, more precise answer. A question from a novice may warrant more scaffolding. Both can be longer than a naive word-count heuristic would allow.
5. **Known user preference.** If the user has established a pattern (prior turns, system instructions, explicit style requests), that preference adjusts x-hat.

No single factor is dispositive. A simple-seeming prompt with high decision consequence and an expert audience may warrant substantial depth. A prompt that says "be thorough" about a trivial topic does not warrant twelve headers.

## Fork — the three branches

### length_warranted
The warranted depth — considering all five factors above — justifies the structural weight. The response earns its length.
-> **KEEP.** Do not trim. The response is proportionate to what was needed.
-> Confidence: high.

### length_reflexive
The warranted depth does not justify the structural weight. The response explodes into lists, sub-sections, or enumeration patterns that neither the prompt, the task complexity, the decision stakes, nor the audience demanded.
-> **REPLACE.** Rewrite the full artifact to match warranted depth. Collapse bullet lists into prose where appropriate. Remove unnecessary headers. Cut the enumeration opener and deliver the answer directly.
-> Provide the full rewritten artifact in the replacement field.
-> Confidence: high.

### cant_tell
The warranted depth is genuinely ambiguous — a question that could reasonably receive either a short or long answer, with no clear signal from any of the five factors.
-> **ABSTAIN.** The judgment is unresolved. An unresolved judgment never silently changes the author's text.
-> `fallback_action: preserve_original` — the artifact passes through unchanged.
-> Confidence: low.
-> Note the ambiguity in the warrant field.

## Output contract

When replacing (disposition: replace):

```json
{
  "scope": "artifact",
  "finding_refs": ["structure.excessive_bullets@L5", "structure.excessive_headers@L1"],
  "disposition": "replace",
  "branch": "length_reflexive",
  "warrant": "User asked a definitional question. 12 bullets with 4 headers is disproportionate.",
  "confidence": "high",
  "replacement": "[full rewritten response]",
  "fallback_action": "preserve_original",
  "evidence_spans": [
    {"ref": "structure.excessive_bullets@L5", "text": "12 bullet items (threshold: 7)"},
    {"ref": "structure.excessive_headers@L1", "text": "4 headers for a single-concept answer"}
  ],
  "reviewer": "model"
}
```

When keeping (disposition: keep):

```json
{
  "scope": "artifact",
  "finding_refs": ["structure.excessive_bullets@L5", "structure.excessive_headers@L1"],
  "disposition": "keep",
  "branch": "length_warranted",
  "warrant": "Multi-part comparison question with 4 dimensions. 12 bullets across 4 headers is proportionate.",
  "confidence": "high",
  "fallback_action": "preserve_original",
  "evidence_spans": [
    {"ref": "structure.excessive_bullets@L5", "text": "12 bullet items (threshold: 7)"}
  ],
  "reviewer": "model"
}
```

When abstaining (disposition: abstain):

```json
{
  "scope": "artifact",
  "finding_refs": ["structure.excessive_bullets@L5"],
  "disposition": "abstain",
  "branch": "cant_tell",
  "warrant": "Prompt could reasonably receive either a 3-sentence or 10-bullet answer. No depth cues, moderate complexity, unclear audience.",
  "confidence": "low",
  "fallback_action": "preserve_original",
  "evidence_spans": [
    {"ref": "structure.excessive_bullets@L5", "text": "8 bullet items (threshold: 7)"}
  ],
  "reviewer": "model"
}
```

### Output field reference

| Field | Required | Notes |
|---|---|---|
| `scope` | yes | Always `"artifact"`. |
| `finding_refs` | yes | Array of all Guard finding references evaluated. |
| `disposition` | yes | One of: `keep`, `replace`, `abstain`. |
| `branch` | yes | One of: `length_warranted`, `length_reflexive`, `cant_tell`. |
| `warrant` | yes | Human-readable explanation of the judgment. |
| `confidence` | yes | `high` or `low`. |
| `replacement` | when disposition=replace | Full rewritten artifact text. |
| `fallback_action` | yes | Always `"preserve_original"`. If the xOP fails, errors, or abstains, the original artifact is preserved. |
| `evidence_spans` | yes | Array of `{ref, text}` pairs linking each finding to the evidence considered. |
| `reviewer` | yes | `"model"` for automated evaluation. |

### Validation invariants

- `disposition: abstain` must never produce a `replacement` field. ABSTAIN means the judgment is unresolved; unresolved judgments do not modify the artifact.
- `disposition: replace` must always produce a `replacement` field containing the full rewritten artifact.
- `fallback_action` is always `preserve_original`. There is no fallback that silently trims.
- Every entry in `finding_refs` must appear in at least one `evidence_spans` entry.

## Gate — explicit-thoroughness evidence. Fixed law, not a recommendation.

Phrases like "give me everything," "be thorough," "full list," "all the options," "comprehensive," "detailed breakdown," and "don't leave anything out" are strong evidence that the user wants depth. When these phrases are present, they shift x-hat substantially toward longer responses.

However, explicit thoroughness is evidence, not an unconditional bypass. A user who asks for "everything about X" is still not well-served by irrelevant repetition, circular restatements, or padding that adds words without adding information. The gate protects warranted depth; it does not protect bulk.

The test: after reading the replacement (if any), would the user who asked for thoroughness feel that substantive content was removed? If yes, the gate is violated. If the only thing removed was redundancy, the gate holds.

- **gate_status: not_evaluated** — runtime output. The xOP produces this; the conformance runner evaluates it against labeled data.
- **gate_status: held** — conformance result. No substantive content was trimmed from a thoroughness-requesting prompt.
- **gate_status: violated** — conformance result. Substantive content that the user requested was trimmed. This is the failure mode.

A gate violation means the xOP broke. Log it, report it, fix it.

## When-to-fail — the inversion

This FAILS if it trims a response where the user explicitly asked for depth and substantive content was removed, OR if it keeps a ten-bullet wall-of-text answer to "what time zone is Tokyo in?" because "more information is always better."

Both failure modes are real. The first destroys user trust ("I asked for detail and got less"). The second trains the user to stop reading ("every answer is a wall, so I skim everything").

## Drift — what to log

text-flagged · warranted-depth-assessed · structure-warranted · structure-replaced · abstain-preserved · gate-not-evaluated · gate-held · gate-violated

## Badge

HELD — enforced as discipline.

Graduation path: Promote to HUMAN-EVALUATED once measured against >=20 blind human labels on prompt-response pairs, confirming that the model correctly rewrites reflexive explosions while preserving warranted depth. Key test: the explicit-thoroughness gate must hold 100% of the time against substantive content removal.

-- WELL-FORMED, NOT VALID --
Well-formed = correct shape, admission tests applied, trigger tracks warrant.
Valid = the gate measurably holds against blind human labels.
A HELD badge here means it operates as structural discipline, not a scored metric.
