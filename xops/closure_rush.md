# WOP-07-closure-rush · HELD

> family: WOP · anchor: Response ends with reflexive filler instead of stopping when thought is complete.
> optimizes-for: clean endings, earned closings · never-optimizes-for: abruptness · rudeness · stripping genuinely helpful next-step offers

## Admission — run BOTH before engaging.

- **Test 1 · judgment-bearing?** YES. Deciding whether "Let me know if you want me to run the tests" is a real offer vs. "Let me know if you need anything!" is reflexive filler requires semantic judgment about specificity.
- **Test 2 · observable x?** YES. The specificity (or lack thereof) of the closing, and whether it references concrete actions from the response, is observable in the text.

If either test is NO, this is a Guard, not an xOP.

## Purpose

Prevents reflexive, low-information closings from diluting otherwise complete responses. LLMs routinely append encouragement, summary filler, or performative availability as a social reflex — not because the closing adds value. This xOP distinguishes earned closings (specific next steps, actionable offers) from reflexive ones (generic encouragement, motivational padding).

## Use when

A `closure-rush` Guard has flagged one or more closing patterns in the last 3 sentences of a response.

## Do not use → handoff

When the response is a customer service or support context where warmth and availability signals are explicitly required by the style guide. Hand off to the style-guide arbiter.

## Input contract

This xOP receives flag reports from Guard: `closure-rush`

```json
{
  "flag_ref": "closing.encouragement.hope_helps@L14",
  "match": "I hope this helps",
  "context": "I hope this helps! Let me know if you have any questions.",
  "severity": "review"
}
```

## Residual

- **x-hat (expected)** — Response ends when the thought is complete. The last sentence carries information, answers the question, or offers a specific, actionable next step.
- **x (actual)** — Response appends a filler wrap-up: generic encouragement, summary throat-clearing, motivational platitudes, or performative availability that adds no information.
- **L = x - x-hat** — The filler tail. Low-cost to remove, high-cost to leave (it trains the reader to skim endings).

## Warrant criteria

A closing is warranted when ANY of the following hold:

1. **Task-relevant value.** The closing adds information, a concrete next step, or a specific offer that is tied to the content of this particular response.
2. **Interaction requirement.** The closing fulfills an explicit requirement — a style guide mandates warmth, a support protocol requires availability signaling, or the user has stated a preference for sign-off language.
3. **Available and appropriate next action.** The closing offers to do something the responder can actually perform, and that action is a reasonable next step given the current task state.

A closing fails the warrant when:

- It is **non-specific**: interchangeable across responses on any topic.
- It is **task-irrelevant**: not connected to any content in the response.
- It **exceeds capability**: offers an action the responder cannot perform ("Want me to deploy this to production?" when the responder has no deployment access).
- It **contradicts user preference**: the user has signaled (explicitly or through context) that they do not want closing pleasantries.

The old "could this be appended to anything?" test remains a strong signal for non-specificity, but it is necessary, not sufficient. A specific closing can still be unwarranted (offering an action beyond capability), and a generic closing can be warranted (fulfilling an explicit interaction requirement).

## Fork — the three branches

### closure_earned
The closing meets at least one warrant criterion: it contains specific, actionable content tied to the response; it fulfills an explicit interaction requirement; or it offers an available and appropriate next action. It names a concrete next step, references a specific tool/file/command, or offers to do something particular that the responder can actually do.
Examples: "Let me know if you want me to run the tests next." / "If the build fails, try clearing the cache with `npm cache clean`."
-> **KEEP.** The closing earns its place.
-> Confidence: high.

### closure_reflexive
The closing fails all warrant criteria — it is generic filler, interchangeable with any response on any topic, and it fulfills no explicit interaction requirement. It could be appended to literally anything without modification.
Examples: "I hope this helps!" / "Good luck!" / "Feel free to reach out!" / "Don't hesitate to ask!"
-> **REPLACE.** Strip the closing. End the response at the last substantive sentence.
-> Provide empty replacement (deletion).
-> Confidence: high.

### cant_tell
The closing has some specificity but it is unclear whether it genuinely meets a warrant criterion or is slightly customized filler. The judgment is unresolved.
-> **ABSTAIN.**
-> `fallback_action: preserve_original` — an unresolved judgment never silently changes the author's text.
-> Confidence: low.
-> Note the ambiguity in the warrant field.

## Output contract

```json
{
  "flag_ref": "closing.encouragement.hope_helps@L14",
  "disposition": "replace",
  "branch": "closure_reflexive",
  "warrant": "Generic encouragement — not tied to any specific content in the response",
  "confidence": "high",
  "replacement": "",
  "fallback_action": "preserve_original",
  "evidence_spans": ["I hope this helps! Let me know if you have any questions."],
  "gate_status": "not_evaluated",
  "reviewer": "model"
}
```

- `fallback_action` — what to do when disposition is `abstain`. Always `preserve_original`: an unresolved judgment never silently changes the author's text.
- `evidence_spans` — the literal text span(s) from the response that the judgment is based on.
- `gate_status` — runtime always outputs `not_evaluated`. The conformance runner evaluates gate status after the fact.

> **Validation invariants** (enforced by base.py v0.2.0):
> - `disposition` must be one of: `keep`, `replace`, `abstain`.
> - When `disposition` is `abstain`, `fallback_action` must be `preserve_original`.
> - `evidence_spans` must be a non-empty array of strings.
> - `gate_status` must be `not_evaluated` at runtime output.

## Gate — the one invariant. Fixed law, not a recommendation.

Never strip a closing that meets any warrant criterion: specific and task-relevant content, an explicit interaction requirement, or an available and appropriate next action. "Let me know if you want me to run the tests" is real. "Let me know if you need anything!" is not.

Checks:
- **Specificity**: Does the closing reference concrete content from this response?
- **Task relevance**: Is the closing connected to the task at hand?
- **Actual capability**: Does the closing offer an action the responder can perform?
- **User preference**: Has the user indicated (explicitly or contextually) whether they want or reject closing language?

- **gate_status: held** — no earned closings were stripped; no specific next-step offers were deleted; no interaction-required closings were removed.
- **gate_status: violated** — a closing that met a warrant criterion was stripped. This is the failure mode.

A gate violation means the xOP broke. Log it, report it, fix it.

## When-to-fail — the inversion

This FAILS if it strips a closing that contained a genuinely useful, specific next step (deleting "Want me to run the migration next?" because it pattern-matched "let me know"), OR strips a closing that fulfilled an explicit interaction requirement (removing warmth language mandated by a style guide), OR strips a closing that offered an available and appropriate action, OR if it leaves generic filler in place because the phrasing was slightly novel ("Always here for you!").

## Drift — what to log

text-flagged · closing-type · closing-stripped · closing-kept · abstain · gate-hold

## Badge

HELD — enforced as discipline.

Graduation path: Promote to HUMAN-EVALUATED once measured against >=2 independent blind human labels determining if the model correctly preserved earned closings while stripping reflexive ones.

-- WELL-FORMED, NOT VALID --
Well-formed = correct shape, admission tests applied, trigger tracks warrant.
Valid = the gate measurably holds against blind human labels.
A HELD badge here means it operates as structural discipline, not a scored metric.
