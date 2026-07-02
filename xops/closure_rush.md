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

## Fork — the three branches

### closure_earned
The closing contains specific, actionable content tied to the response. It names a concrete next step, references a specific tool/file/command, or offers to do something particular.
Examples: "Let me know if you want me to run the tests next." / "If the build fails, try clearing the cache with `npm cache clean`."
-> **KEEP.** The closing earns its place.
-> Confidence: high.

### closure_reflexive
The closing is generic filler — interchangeable with any response on any topic. It could be appended to literally anything without modification.
Examples: "I hope this helps!" / "Good luck!" / "Feel free to reach out!" / "Don't hesitate to ask!"
-> **REPLACE.** Strip the closing. End the response at the last substantive sentence.
-> Provide empty replacement (deletion).
-> Confidence: high.

### cant_tell
The closing has some specificity but it is unclear whether it is genuinely earned or just slightly customized filler.
-> **ABSTAIN, toward stripping.** Filler closings are low-cost to remove — a clean ending never hurts. A reflexive closing sometimes does.
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
  "reviewer": "model"
}
```

## Gate — the one invariant. Fixed law, not a recommendation.

Never strip a closing that contains specific, actionable next steps. "Let me know if you want me to run the tests" is real. "Let me know if you need anything!" is not. The test: could this closing be appended to any response without modification? If yes, it is reflexive. If no, it is earned.

- **gate_status: held** — no earned closings were stripped; no specific next-step offers were deleted.
- **gate_status: violated** — a closing with concrete, response-specific content was stripped. This is the failure mode.

A gate violation means the xOP broke. Log it, report it, fix it.

## When-to-fail — the inversion

This FAILS if it strips a closing that contained a genuinely useful, specific next step (deleting "Want me to run the migration next?" because it pattern-matched "let me know") OR if it leaves generic filler in place because the phrasing was slightly novel ("Always here for you!").

## Drift — what to log

text-flagged · closing-type · closing-stripped · closing-kept · abstain · gate-hold

## Badge

HELD — enforced as discipline.

Graduation path: Promote to HUMAN-EVALUATED once measured against >=2 independent blind human labels determining if the model correctly preserved earned closings while stripping reflexive ones.

-- WELL-FORMED, NOT VALID --
Well-formed = correct shape, admission tests applied, trigger tracks warrant.
Valid = the gate measurably holds against blind human labels.
A HELD badge here means it operates as structural discipline, not a scored metric.
