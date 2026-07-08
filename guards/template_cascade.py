#!/usr/bin/env python3
"""
template_cascade.py — Guard for reflexive structural scaffolding (v0.1.0).

Catches the "template cascade" pattern: the model structures every response
with the same boilerplate scaffolding regardless of whether it serves the
content — template openings, formulaic transitions, structural padding,
and meta-narration.

Scanning rules:
  - Template openings: scanned in FIRST 2 sentences only.
  - Formulaic transitions, structural padding, meta-narration: scanned
    throughout the full response.
  - Code fences and inline code are excluded.
  - All flags are severity "review" (need xOP judgment).

Badge: FIXTURE-TESTED.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Import from framework
sys.path.insert(0, str(Path(__file__).parent.parent))
from guards.base import Guard, GuardReport, Flag, run_guard_cli


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _strip_code_fences(text: str) -> str:
    """Blank out fenced code blocks so we don't flag code examples.

    Replaces non-newline characters with spaces rather than deleting them so
    that character offsets and line numbers remain valid for subsequent callers.
    """
    return re.sub(r"```[\s\S]*?```", lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)


def _strip_inline_code(text: str) -> str:
    """Remove inline code so we don't flag variable names."""
    return re.sub(r"`[^`]+`", "", text)


def _line_of(text: str, idx: int) -> int:
    """1-based line number for a character index."""
    return text.count("\n", 0, idx) + 1


def _extract_context(text: str, start: int, end: int) -> str:
    """Extract the sentence surrounding a match for xOP judgment."""
    ctx_start = start
    while ctx_start > 0 and text[ctx_start - 1] not in '.!?\n':
        ctx_start -= 1

    ctx_end = end
    while ctx_end < len(text) and text[ctx_end] not in '.!?\n':
        ctx_end += 1

    return text[ctx_start:ctx_end].strip()


def _first_two_sentences(text: str) -> str:
    """Extract roughly the first two sentences of text."""
    # Split on sentence-ending punctuation followed by whitespace
    parts = re.split(r'(?<=[.!?])\s+', text.strip(), maxsplit=2)
    if len(parts) <= 2:
        return text.strip()
    return parts[0] + " " + parts[1]


# ---------------------------------------------------------------------------
# TIER 1 — TEMPLATE OPENINGS (scanned in first 2 sentences only)
# ---------------------------------------------------------------------------
def _rx(p): return re.compile(p, re.IGNORECASE)

TEMPLATE_OPENINGS = [
    ("great_question",       _rx(r"^[\s]*(?:that'?s\s+a\s+)?great\s+question\s*[!.]?")),
    ("interesting_topic",    _rx(r"^[\s]*what\s+(?:a|an)\s+(?:great|interesting|thoughtful|excellent|wonderful|fantastic)\s+(?:question|topic|observation|point)\s*[!.]?")),
    ("sure_opener",          _rx(r"^[\s]*sure\s*[!.]")),
    ("of_course_opener",     _rx(r"^[\s]*of\s+course\s*[!.]")),
    ("certainly_opener",     _rx(r"^[\s]*certainly\s*[!.]")),
    ("absolutely_opener",    _rx(r"^[\s]*absolutely\s*[!.]")),
    ("happy_to_help",        _rx(r"^[\s]*I'?d?\s+(?:be\s+)?(?:happy|glad|love)\s+to\s+help(?:\s+(?:with\s+that|you))?\s*[!.]?")),
    ("thanks_for_asking",    _rx(r"^[\s]*thanks?\s+(?:for\s+(?:asking|sharing|bringing|raising)|you\s+for\s+(?:asking|sharing|bringing|raising))\s*[!.]?")),
]

# ---------------------------------------------------------------------------
# TIER 2 — FORMULAIC TRANSITIONS (scanned throughout)
# ---------------------------------------------------------------------------
FORMULAIC_TRANSITIONS = [
    ("now_lets",             _rx(r"\bnow,?\s+let'?s\s+(?:look|turn|move|explore|examine|consider|discuss)\b")),
    ("moving_on_to",         _rx(r"\bmoving\s+on\s+to\b")),
    ("with_that_in_mind",    _rx(r"\bwith\s+that\s+in\s+mind\b")),
    ("building_on_that",     _rx(r"\bbuilding\s+on\s+that\b")),
    ("that_brings_us",       _rx(r"\bthat\s+brings\s+us\s+to\b")),
    ("lets_explore",         _rx(r"\blet'?s\s+explore\b")),
    ("another_key",          _rx(r"\banother\s+(?:key|important|critical|crucial|notable)\s+(?:aspect|point|factor|consideration|thing|element)\s+(?:is|to)\b")),
    ("worth_mentioning",     _rx(r"\b(?:it'?s\s+)?(?:also\s+)?worth\s+mentioning\b")),
    ("lets_take_a_look",     _rx(r"\blet'?s\s+(?:take\s+a\s+(?:closer\s+)?look|turn\s+our\s+attention)\b")),
    ("on_that_note",         _rx(r"\bon\s+that\s+note\b")),
    ("speaking_of",          _rx(r"(^|\.\s+)speaking\s+of\b")),
]

# ---------------------------------------------------------------------------
# TIER 3 — STRUCTURAL PADDING (scanned throughout)
# ---------------------------------------------------------------------------
STRUCTURAL_PADDING = [
    ("first_let_me",         _rx(r"\bfirst,?\s+let\s+me\s+(?:explain|start|clarify|address|note|point\s+out)\b")),
    ("before_we_dive",       _rx(r"\bbefore\s+(?:we|I)\s+(?:dive|jump|get)\s+(?:in|into|started)\b")),
    ("to_understand_this",   _rx(r"\bto\s+(?:understand|appreciate|grasp)\s+this,?\s+(?:we|you)\s+(?:need|have|must|should)\b")),
    ("let_me_break",         _rx(r"\blet\s+me\s+break\s+(?:this|it)\s+down\b")),
    ("several_key_points",   _rx(r"\bthere\s+are\s+(?:several|a\s+few|many|some|multiple)\s+(?:key|important|main|critical)\s+(?:points|things|factors|aspects|considerations)\s+to\s+(?:consider|keep\s+in\s+mind|note|address)\b")),
    ("its_important",        _rx(r"\bit'?s\s+(?:important|essential|critical|crucial|vital)\s+to\s+(?:understand|note|remember|recognize|acknowledge|keep\s+in\s+mind)\b")),
    ("lets_start_by",        _rx(r"\blet'?s\s+start\s+(?:by|with)\b")),
]

# ---------------------------------------------------------------------------
# TIER 4 — META-NARRATION (scanned throughout)
# ---------------------------------------------------------------------------
META_NARRATION = [
    ("as_mentioned",         _rx(r"\bas\s+(?:I|we)\s+(?:mentioned|noted|discussed|stated|said|pointed\s+out)\b.{0,40}?\b(?:earlier|above|before|previously)\b")),
    ("as_we_discussed",      _rx(r"\bas\s+(?:we|I)\s+discussed\b")),
    ("going_back_to",        _rx(r"\bgoing\s+back\s+to\b")),
    ("to_circle_back",       _rx(r"\bto\s+circle\s+back\b")),
    ("as_you_can_see",       _rx(r"\bas\s+you\s+can\s+see\b")),
    ("recall_that",          _rx(r"\b(?:recall|remember)\s+that\s+(?:we|I|earlier)\b")),
]


class TemplateCascadeGuard(Guard):
    """
    Guard for reflexive template scaffolding.

    Catches template openings (first 2 sentences), formulaic transitions,
    structural padding, and meta-narration (throughout). All flags are
    severity "review" — judgment on whether structure is purposeful
    belongs to the xOP.
    """

    @property
    def guard_id(self) -> str:
        return "template-cascade"

    @property
    def version(self) -> str:
        return "0.1.0"

    def scan(self, text: str, **kwargs) -> GuardReport:
        report = GuardReport(guard_id=self.guard_id, version=self.version)

        # Strip code fences and inline code before scanning
        scannable = _strip_code_fences(text)
        scannable = _strip_inline_code(scannable)

        if not scannable.strip():
            return report

        # --- Template openings: first 2 sentences only ---
        opening_text = _first_two_sentences(scannable)
        for name, rx in TEMPLATE_OPENINGS:
            for m in rx.finditer(opening_text):
                frag = m.group(0).strip()
                frag = (frag[:57] + "...") if len(frag) > 60 else frag
                report.flags.append(Flag(
                    rule_id=f"opening.{name}",
                    tier="opening",
                    severity="review",
                    match=frag,
                    line=_line_of(scannable, m.start()),
                    context=_extract_context(scannable, m.start(), m.end()),
                ))

        # --- Formulaic transitions: full text ---
        for name, rx in FORMULAIC_TRANSITIONS:
            for m in rx.finditer(scannable):
                frag = m.group(0).strip()
                frag = (frag[:57] + "...") if len(frag) > 60 else frag
                report.flags.append(Flag(
                    rule_id=f"transition.{name}",
                    tier="transition",
                    severity="review",
                    match=frag,
                    line=_line_of(scannable, m.start()),
                    context=_extract_context(scannable, m.start(), m.end()),
                ))

        # --- Structural padding: full text ---
        for name, rx in STRUCTURAL_PADDING:
            for m in rx.finditer(scannable):
                frag = m.group(0).strip()
                frag = (frag[:57] + "...") if len(frag) > 60 else frag
                report.flags.append(Flag(
                    rule_id=f"padding.{name}",
                    tier="padding",
                    severity="review",
                    match=frag,
                    line=_line_of(scannable, m.start()),
                    context=_extract_context(scannable, m.start(), m.end()),
                ))

        # --- Meta-narration: full text ---
        for name, rx in META_NARRATION:
            for m in rx.finditer(scannable):
                frag = m.group(0).strip()
                frag = (frag[:57] + "...") if len(frag) > 60 else frag
                report.flags.append(Flag(
                    rule_id=f"meta.{name}",
                    tier="meta",
                    severity="review",
                    match=frag,
                    line=_line_of(scannable, m.start()),
                    context=_extract_context(scannable, m.start(), m.end()),
                ))

        # --- Advisory: template density metric ---
        words = re.findall(r"\b[\w'-]+\b", scannable)
        report.advisory = {
            "word_count": len(words),
            "template_flags": len(report.flags),
            "flags_per_100_words": round(100 * len(report.flags) / max(len(words), 1), 1),
        }

        return report


# CLI entry point
if __name__ == "__main__":
    guard = TemplateCascadeGuard()
    run_guard_cli(guard)
