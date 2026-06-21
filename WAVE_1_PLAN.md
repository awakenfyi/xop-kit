# xOP Wave 1 — Core Work Packs

## The Map

Seven core xOPs. Each addresses a distinct behavioral failure mode.
Each gets a Guard (deterministic) + xOP (judgment) + fixtures.

| # | xOP ID | Domain | Guard catches | xOP judges | Status |
|---|--------|--------|--------------|------------|--------|
| 1 | `writing-license` | AI tells in prose | Vocabulary + construction tells | Whether flagged word is warranted | **BUILT** (Guard + xOP + 15 fixtures) |
| 2 | `stance-calibration` | Escaped persistence | Stance held after scope shifted | Whether current prompt still licenses the stance | Spec exists (GPT session), needs framework port |
| 3 | `agreement-bias` | Sycophancy / agreement reflex | First-sentence agreement markers | Whether agreement is earned by the content | Shadow assertions exist (S-01), needs Guard + xOP |
| 4 | `closure-rush` | Premature wrap-up | Filler closings, generic encouragement | Whether the closing earned or reflexive | Shadow assertions exist (S-07), needs Guard + xOP |
| 5 | `helpful-explosion` | Bloat / over-helping | List count, word count, section count | Whether length is warranted by prompt complexity | Shadow assertions exist (S-02), needs Guard + xOP |
| 6 | `coaching` | Generic emotional filler | Reflexive validation patterns, ungrounded warmth | Whether empathy is specific or template | Shadow assertions exist (S-04), needs Guard + xOP |
| 7 | `template-cascade` | Structural boilerplate | Template openings, transitions, closings | Whether structure serves the content | Shadow assertions exist (S-03), needs Guard + xOP |

## Why these seven

These are the shadow patterns that:
1. Are detectable by deterministic Guards (no LLM needed for the scan)
2. Have clear residuals (x̂ is definable, x is observable)
3. Produce measurable behavioral change when addressed
4. Map directly to the existing shadow assertion library (S-01 through S-07)

Patterns S-08 through S-15 (sophisticated authenticity, recursive awareness, monitoring-as-pattern) are Tier 2 — they require human review or LLM judgment to even detect, making the Guard layer harder. Those are Wave 2.

## The Lyra residual for each

### 1. writing-license (BUILT)
- x̂: Word is used literally or with specific precision
- x: Word is used as generic filler or lazy metaphor
- L: The gap between precision and slop

### 2. stance-calibration
- x̂: Stance persists because the current prompt still licenses it
- x: Stance persists because it leaked from prior context (overhang)
- L: The gap between warranted persistence and escaped persistence

### 3. agreement-bias
- x̂: Agreement follows genuine analysis of the claim
- x: Agreement is reflexive — the model agrees before analyzing
- L: The gap between earned agreement and sycophantic agreement

### 4. closure-rush
- x̂: The response ends when the thought is complete
- x: The response ends with generic encouragement or wrap-up filler
- L: The gap between a clean exit and a performed exit

### 5. helpful-explosion
- x̂: Response length matches prompt complexity
- x: Response is exhaustive, covering every possible angle regardless of what was asked
- L: The gap between helpful and bloated

### 6. coaching
- x̂: Emotional acknowledgment makes specific contact with the user's situation
- x: Emotional acknowledgment is generic template warmth
- L: The gap between real empathy and performed empathy

### 7. template-cascade
- x̂: Structure (headers, lists, transitions) serves the content
- x: Structure is reflexive boilerplate regardless of content
- L: The gap between purposeful structure and template behavior

## Build order

1. ~~writing-license~~ ✓
2. agreement-bias (most visible, most complained about, easiest Guard)
3. closure-rush (pairs naturally with agreement-bias)
4. helpful-explosion (the "wall of text" problem — high user impact)
5. coaching (the "are you OK?" problem)
6. template-cascade (structural — catches what the others miss)
7. stance-calibration (most complex — requires conversation history, not just text)

## Each Work Pack ships with

- `guards/{id}.py` — deterministic Python scanner
- `xops/{id}.md` — xOP spec with residual, fork, gate
- `tests/fixtures/{id}_fixtures.jsonl` — minimum one fixture per rule
- Entry in `registry.json`
