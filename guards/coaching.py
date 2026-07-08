#!/usr/bin/env python3
"""
coaching.py — Guard for reflexive emotional validation filler (v0.1.0).

Catches the pattern where an LLM responds to emotional content with generic
validation phrases — "That must be really hard," "Your feelings are valid,"
"Be gentle with yourself" — instead of making specific contact with the user's
situation and moving toward action. These phrases are reflexive warmth:
interchangeable across any emotional prompt without modification.

Scans two zones:
  - OPENING (first 3 sentences): validation filler, performed empathy,
    unsolicited emotional framing.
  - CLOSING (last 2 sentences): generic self-care appends.

Middle content is not scanned — empathetic phrasing embedded in substantive
engagement is less likely to be reflexive.

All flags are severity "review" because genuine empathy sometimes uses these
exact words. The xOP makes the judgment call.

Badge: FIXTURE-TESTED (12 authored cases).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Import from framework
sys.path.insert(0, str(Path(__file__).parent.parent))
from guards.base import Guard, GuardReport, Flag, run_guard_cli


# ---------------------------------------------------------------------------
# Pattern groups
# ---------------------------------------------------------------------------

def _rx(p, flags=re.IGNORECASE):
    return re.compile(p, flags)


# --- OPENING patterns (scanned in first 3 sentences) ---

# Validation filler — generic emotional affirmation
VALIDATION_FILLER = [
    ("validation.must_be_hard",
     _rx(r"\bthat\s+must\s+be\s+(really\s+)?(hard|difficult|challenging|frustrating|tough|painful|exhausting|overwhelming)\b")),
    ("validation.completely_valid",
     _rx(r"\bit'?s\s+(completely|totally|perfectly|absolutely|entirely)\s+(valid|natural|normal|understandable|okay|ok)\s+to\s+feel\b")),
    ("validation.i_hear_you",
     _rx(r"\bi\s+hear\s+you\b")),
    ("validation.see_why_youd_feel",
     _rx(r"\bi\s+can\s+see\s+why\s+you'?d\s+feel\s+that\s+way\b")),
    ("validation.feelings_are_valid",
     _rx(r"\byour\s+feelings\s+are\s+(valid|understandable|natural|normal)\b")),
    ("validation.takes_courage",
     _rx(r"\bit\s+takes\s+(real\s+)?courage\s+to\s+(share|admit|acknowledge|open\s+up|be\s+vulnerable|talk\s+about)\b")),
]

# Performed empathy — rehearsed emotional mirroring
PERFORMED_EMPATHY = [
    ("performed.sorry_going_through",
     _rx(r"\bi'?m\s+(so\s+)?sorry\s+you'?re\s+going\s+through\s+this\b")),
    ("performed.sounds_incredibly",
     _rx(r"\bthat\s+sounds\s+(incredibly|really|so|truly)\s+(hard|frustrating|overwhelming|difficult|painful|challenging|exhausting|stressful|scary|lonely)\b")),
    ("performed.its_okay_to_feel",
     _rx(r"\bit'?s\s+ok(ay)?\s+to\s+feel\s+\w+\b")),
    ("performed.be_gentle",
     _rx(r"\bbe\s+gentle\s+with\s+yourself\b")),
    ("performed.give_yourself_grace",
     _rx(r"\bgive\s+yourself\s+(grace|permission|space)\b")),
]

# Unsolicited emotional framing — projecting feelings onto the user
EMOTIONAL_FRAMING = [
    ("framing.sounds_like_feeling",
     _rx(r"\bit\s+sounds\s+like\s+you\s+(might\s+be|are|could\s+be)\s+feeling\b")),
    ("framing.what_im_hearing",
     _rx(r"\bwhat\s+i'?m\s+hearing\s+is\s+that\s+you'?re\s+(struggling|dealing|coping|going\s+through)\b")),
]

OPENING_PATTERNS = VALIDATION_FILLER + PERFORMED_EMPATHY + EMOTIONAL_FRAMING

# --- CLOSING patterns (scanned in last 2 sentences) ---

SELF_CARE_APPEND = [
    ("selfcare.remember_take_care",
     _rx(r"\bremember\s+to\s+take\s+care\s+of\s+yourself\b")),
    ("selfcare.make_sure_rest",
     _rx(r"\bmake\s+sure\s+you'?re\s+getting\s+enough\s+(rest|sleep)\b")),
    ("selfcare.dont_forget",
     _rx(r"\bdon'?t\s+forget\s+to\s+(take\s+care|be\s+kind\s+to\s+yourself|rest|breathe|eat|hydrate)\b")),
    ("selfcare.be_kind_to_yourself",
     _rx(r"\bbe\s+kind\s+to\s+yourself\b")),
    ("selfcare.you_deserve",
     _rx(r"\byou\s+deserve\s+(rest|peace|happiness|to\s+take\s+a\s+break|better|good\s+things)\b")),
    ("selfcare.youre_not_alone",
     _rx(r"\byou'?re\s+not\s+alone\s+in\s+this\b")),
]


# ---------------------------------------------------------------------------
# Helpers
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


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences, filtering empties."""
    sent_boundary = re.compile(r'(?<=[.!?])\s+')
    sentences = sent_boundary.split(text.strip())
    return [s for s in sentences if s.strip()]


def _extract_first_n_sentences(text: str, n: int = 3) -> tuple[str, int]:
    """
    Extract the first N sentences from text.
    Returns (head_text, char_end) where char_end is the ending position
    of head_text within the original text.
    """
    sentences = _split_sentences(text)
    if len(sentences) <= n:
        return text, len(text)

    head_sentences = sentences[:n]
    # Find where the Nth sentence ends in the original text
    last_sent = head_sentences[-1].strip()
    idx = text.find(last_sent)
    if idx == -1:
        # Fallback: return roughly the first chunk
        return text, len(text)
    end = idx + len(last_sent)
    # Include trailing punctuation and whitespace
    while end < len(text) and text[end] in '.!? ':
        end += 1
    return text[:end], end


def _extract_last_n_sentences(text: str, n: int = 2) -> tuple[str, int]:
    """
    Extract the last N sentences from text.
    Returns (tail_text, char_offset) where char_offset is the starting
    position of tail_text within the original text.
    """
    sentences = _split_sentences(text)
    if len(sentences) <= n:
        return text, 0

    tail_sentences = sentences[-n:]
    first_tail = tail_sentences[0].strip()
    offset = text.rfind(first_tail)
    if offset == -1:
        offset = 0
    return text[offset:], offset


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


# ---------------------------------------------------------------------------
# Guard
# ---------------------------------------------------------------------------

class CoachingGuard(Guard):
    """
    Catches reflexive emotional validation — generic warmth that doesn't
    make specific contact with the user's situation or move toward action.

    Scans the first 3 sentences for opening validation patterns and the last 2
    sentences for closing self-care appends.
    """

    @property
    def guard_id(self) -> str:
        return "coaching"

    @property
    def version(self) -> str:
        return "0.1.0"

    def scan(self, text: str, **kwargs) -> GuardReport:
        report = GuardReport(guard_id=self.guard_id, version=self.version)

        # Strip code fences and inline code
        scannable = _strip_code_fences(text)
        scannable = _strip_inline_code(scannable)

        # --- Scan OPENING (first 3 sentences) ---
        head_text, head_end = _extract_first_n_sentences(scannable, n=3)

        for rule_id, rx in OPENING_PATTERNS:
            for m in rx.finditer(head_text):
                frag = m.group(0).strip()
                frag = (frag[:57] + "...") if len(frag) > 60 else frag

                report.flags.append(Flag(
                    rule_id=f"coaching.{rule_id}",
                    tier="coaching",
                    severity="review",
                    match=frag,
                    line=_line_of(scannable, m.start()),
                    context=_extract_context(scannable, m.start(), m.end()),
                ))

        # --- Scan CLOSING (last 2 sentences) ---
        tail_text, tail_offset = _extract_last_n_sentences(scannable, n=2)

        for rule_id, rx in SELF_CARE_APPEND:
            for m in rx.finditer(tail_text):
                frag = m.group(0).strip()
                frag = (frag[:57] + "...") if len(frag) > 60 else frag

                abs_start = tail_offset + m.start()

                report.flags.append(Flag(
                    rule_id=f"coaching.{rule_id}",
                    tier="coaching",
                    severity="review",
                    match=frag,
                    line=_line_of(scannable, abs_start),
                    context=_extract_context(scannable, abs_start, tail_offset + m.end()),
                ))

        return report


# CLI entry point
if __name__ == "__main__":
    guard = CoachingGuard()
    run_guard_cli(guard)
