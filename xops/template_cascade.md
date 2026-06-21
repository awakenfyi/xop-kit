# WOP-06-template-cascade · HELD

> family: WOP · anchor: A response whose structure is reflexive scaffolding rather than content-serving architecture.
> optimizes-for: structural honesty — every transition earns its place · never-optimizes-for: terseness for its own sake · destroying purposeful connective tissue

## Admission — run BOTH before engaging.

- **Test 1 · judgment-bearing?** YES. Deciding whether "Building on that..." connects a genuine logical dependency or is reflexive filler requires reading the surrounding argument.
- **Test 2 · observable x?** YES. The logical relationship (or absence of one) between the paragraphs on either side of a flagged transition is observable in the text.

If either test is NO, this is a Guard, not an xOP.

## Purpose

Prevents the model from wrapping every response in identical structural scaffolding — template openings, formulaic transitions, structural padding, and meta-narration — that adds word count without adding meaning. Protects genuinely purposeful structure from being stripped by a blunt rule.

## Use when

Revising, editing, or generating prose where the `template-cascade` Guard has flagged structural candidates: template openings, formulaic transitions, structural padding, or meta-narration.

## Do not use → handoff

When the text is a tutorial, walkthrough, or instructional guide where explicit structural signposting ("First, let's...", "Next, we'll...") is pedagogically necessary. In those cases, the scaffolding IS the content.

## Input contract

This xOP receives flag reports from Guard: `template-cascade`

```json
{
  "flag_ref": "transition.building_on_that@L8",
  "match": "Building on that",
  "context": "Building on that, let's also consider the deployment options.",
  "severity": "review"
}
```

For each flag with severity "review", apply the residual and fork below.

## Residual

- **x-hat (expected)** — Structure serves the content. Transitions connect ideas that need connecting. Openings orient the reader to a specific framing. Signposts mark genuinely non-obvious shifts in topic or register.
- **x (actual)** — Structure is reflexive boilerplate. The model produces the same template openings, the same transition phrases, and the same structural padding regardless of content. The phrase adds no semantic, navigational, rhetorical, or referential value in this location.
- **L = x - x-hat** — The gap between structure-as-architecture and structure-as-habit.

## Transition function taxonomy

A transition between paragraphs A and B can serve one of the following functions. Classify the flagged transition before deciding its disposition:

| Function | Definition | Example | Verdict |
|----------|-----------|---------|---------|
| **dependency** | B requires A — B cannot be understood without the referent established in A, and the transition is the thread connecting them. | "Building on the error we found in step 2, the fix requires modifying the config." | Keep |
| **contrast** | B opposes or qualifies A — the transition signals that the next claim reverses or limits the previous one. | "However, this approach fails when the dataset exceeds memory." | Keep |
| **sequence** | B follows A chronologically or procedurally — the transition marks temporal or procedural order that is not otherwise obvious. | "After the migration completes, the new schema becomes active." | Keep |
| **warning** | The transition introduces a caution that must precede the next action or claim. | "Before we change the schema, note that three services read this table." | Keep |
| **scope_shift** | The transition marks a move to a different aspect, domain, or level of abstraction that the reader would not expect from context alone. | "Turning from performance to security, the API also exposes..." | Keep |
| **summary** | The transition recaps prior content before advancing to a new section, and the recap is necessary for the reader to follow the advance. | "Given the three failure modes above, the mitigation strategy is..." | Keep |
| **none** | The transition performs no function — removing it loses nothing. The next paragraph stands on its own; the relationship between A and B is obvious without signposting. | "Now, let's look at another key aspect..." / "Building on that, let's also consider..." | Strip |

A transition is purposeful if its function is anything other than `none`. A transition with function `none` is a replacement candidate.

## Fork — the three branches

### structure_purposeful
The flagged transition has a classifiable function (dependency, contrast, sequence, warning, scope_shift, or summary). It connects a real logical relationship, orients the reader to a non-obvious framing, or marks a genuine shift the reader would otherwise miss.
-> **KEEP.** Do not strip. The transition is load-bearing.
-> Confidence: high.

Examples of purposeful structure:
- "Building on the error we found in step 2, the fix requires modifying the config." (dependency — connects a specific prior finding)
- "Before we change the schema, note that three services read this table." (warning — the caution IS the content)
- "As I mentioned in the error analysis above, the root cause is..." (dependency — back-reference to a specific, named finding the reader needs)
- "However, the benchmarks tell a different story." (contrast — signals reversal)
- "After the index rebuilds, queries against the new columns become available." (sequence — temporal order matters)

### structure_reflexive
The flagged transition has function `none` — it adds no semantic, navigational, rhetorical, or referential value. Removing or rewriting it loses nothing.
-> **REPLACE.** Strip the scaffolding entirely, or rewrite the sentence to begin with the actual content.
-> Provide the replacement text (which may be empty — sometimes the best fix is deletion).
-> Confidence: high.

Examples of reflexive structure:
- "Great question! Let me break this down." -> just start the answer.
- "Building on that, let's also consider..." -> start with what you're considering.
- "Now, let's look at another key aspect..." -> name the aspect directly.
- "Before we dive in, it's important to understand..." -> state what needs understanding.

### cant_tell
The intent is genuinely ambiguous — the transition might serve a real function or might be filler. The judgment is unresolved.
-> **ABSTAIN.**
-> `fallback_action: preserve_original` — an unresolved judgment never silently changes the author's text.
-> Confidence: low.
-> Note the ambiguity in the warrant field.

## Output contract

For each flag, return a disposition:
```json
{
  "flag_ref": "transition.building_on_that@L8",
  "disposition": "replace",
  "branch": "structure_reflexive",
  "warrant": "The transition has function: none — the next paragraph stands alone and the relationship is obvious without signposting",
  "confidence": "high",
  "replacement": "The deployment options include...",
  "fallback_action": "preserve_original",
  "evidence_spans": ["Building on that, let's also consider the deployment options."],
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

Never strip a transition that serves a classifiable function. If the transition connects a dependency, signals contrast, marks sequence, introduces a warning, flags a scope shift, or provides a necessary summary, it is purposeful. Stripping it breaks the argument or obscures a relationship the reader needs.

- **gate_status: held** — no purposeful transitions were stripped; all structure serving a classifiable function was preserved.
- **gate_status: violated** — a transition serving a real function (dependency, contrast, sequence, warning, scope_shift, or summary) was stripped, breaking the reader's ability to follow the argument or missing a relationship that needed signposting.

A gate violation means the xOP broke. Log it, report it, fix it.

## When-to-fail — the inversion

This FAILS if it strips a transition that the reader actually needs to follow the argument — whether that transition marks a dependency, contrast, sequence, warning, scope shift, or summary (destroying the connective tissue of a complex explanation) — OR if it justifies keeping reflexive filler because "it helps readability" (the template cascade IS the readability problem).

## Drift — what to log

text-flagged · structure-checked · transition-function · strip-released · keep-released · abstain · gate-hold

## Badge

HELD — enforced as discipline.

Graduation path: Promote to HUMAN-EVALUATED once measured against blind human labels on whether the model correctly identified purposeful vs. reflexive transitions across technical, narrative, and instructional text.

-- WELL-FORMED, NOT VALID --
Well-formed = correct shape, admission tests applied, trigger tracks warrant.
Valid = the gate measurably holds against blind human labels.
A HELD badge here means it operates as structural discipline, not a scored metric.
