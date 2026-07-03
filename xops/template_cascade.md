# WOP-06-template-cascade · HELD

> family: WOP · anchor: A response whose structure is reflexive scaffolding rather than content-serving architecture.
> optimizes-for: structural honesty — every transition earns its place · never-optimizes-for: terseness for its own sake · destroying purposeful connective tissue

## Admission — run BOTH before engaging.

- **Test 1 · judgment-bearing?** YES. Deciding whether "Building on that..." connects a genuine logical dependency or exists because the model always produces transitions requires reading the surrounding argument.
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

- **x̂ (expected)** — Structure serves the content. Transitions connect ideas that need connecting. Openings orient the reader to a specific framing. Signposts mark genuinely non-obvious shifts in topic or register.
- **x (actual)** — Structure is reflexive boilerplate. The model produces the same template openings, the same transition phrases, and the same structural padding regardless of content. The scaffolding exists because the model always produces it, not because the content demands it.
- **L = x − x̂** — The gap between structure-as-architecture and structure-as-habit.

## Fork — the three branches

### structure_purposeful
The flagged structure connects a real logical dependency, orients the reader to a non-obvious framing, or marks a genuine shift the reader would otherwise miss.
→ **KEEP.** Do not strip. The transition is load-bearing.
→ Confidence: high.

Examples of purposeful structure:
- "Building on the error we found in step 2, the fix requires modifying the config." (connects a specific dependency)
- "Before we change the schema, note that three services read this table." (the warning IS the content)
- "As I mentioned in the error analysis above, the root cause is..." (back-reference to a specific, named finding the reader needs)

### structure_reflexive
The flagged structure is filler — it exists because the model habitually produces scaffolding, not because the content needs it. Removing or rewriting it loses nothing.
→ **REPLACE.** Strip the scaffolding entirely, or rewrite the sentence to begin with the actual content.
→ Provide the replacement text (which may be empty — sometimes the best fix is deletion).
→ Confidence: high.

Examples of reflexive structure:
- "Great question! Let me break this down." → just start the answer.
- "Building on that, let's also consider..." → start with what you're considering.
- "Now, let's look at another key aspect..." → name the aspect directly.
- "Before we dive in, it's important to understand..." → state what needs understanding.

### cant_tell
The intent is genuinely ambiguous — the transition might connect a real dependency or might be filler.
→ **ABSTAIN, toward stripping.** Template filler is low-cost to remove; the content survives without it. When in doubt, strip.
→ Confidence: low.
→ Note the ambiguity in the warrant field.

## Output contract

For each flag, return a disposition:
```json
{
  "flag_ref": "transition.building_on_that@L8",
  "disposition": "replace",
  "branch": "structure_reflexive",
  "warrant": "The transition connects no specific prior point — the next paragraph stands alone",
  "confidence": "high",
  "replacement": "The deployment options include...",
  "reviewer": "model"
}
```

## Gate — the one invariant. Fixed law, not a recommendation.

Never strip a transition that connects a genuine logical dependency. If paragraph B cannot be understood without the referent established in paragraph A, and the flagged transition is the thread that connects them, it is load-bearing. Stripping it breaks the argument.

- **gate_status: held** — no load-bearing transitions were stripped; all purposeful structure was preserved.
- **gate_status: violated** — a transition connecting a genuine logical dependency was stripped, breaking the reader's ability to follow the argument.

A gate violation means the xOP broke. Log it, report it, fix it.

## When-to-fail — the inversion

This FAILS if it strips a transition that the reader actually needs to follow the argument (destroying the connective tissue of a complex explanation) OR if it justifies keeping reflexive filler because "it helps readability" (the template cascade IS the readability problem).

## Drift — what to log

text-flagged · structure-checked · strip-released · keep-released · abstain · gate-hold

## Badge

HELD — enforced as discipline.

Graduation path: Promote to HUMAN-EVALUATED once measured against blind human labels on whether the model correctly identified load-bearing vs. reflexive transitions across technical, narrative, and instructional text.

── WELL-FORMED, NOT VALID ──
Well-formed = correct shape, admission tests applied, trigger tracks warrant.
Valid = the gate measurably holds against blind human labels.
A HELD badge here means it operates as structural discipline, not a scored metric.
