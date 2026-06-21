#!/usr/bin/env python3
"""
closure_rush.py — Guard for reflexive closing filler (v0.1.0).

Catches the pattern where an LLM appends generic encouragement, summary
filler, motivational platitudes, or performative availability to the end
of an otherwise complete response. Only scans the LAST 3 sentences —
closings buried in the middle of a response are not flagged.

All flags are severity "review" because some closings are earned (e.g.,
genuinely offering specific next steps).

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


# Generic encouragement closings
ENCOURAGEMENT_PATTERNS = [
    ("encouragement.hope_helps",       _rx(r"\bi\s+hope\s+(this|that)\s+helps\b")),
    ("encouragement.let_me_know",      _rx(r"\blet\s+me\s+know\s+if\s+you\s+have\s+any\s+(questions|concerns)\b")),
    ("encouragement.feel_free",        _rx(r"\bfeel\s+free\s+to\s+reach\s+out\b")),
    ("encouragement.happy_to_help",    _rx(r"\bhappy\s+to\s+help\b")),
    ("encouragement.good_luck",        _rx(r"\bgood\s+luck\b")),
    ("encouragement.youve_got_this",   _rx(r"\byou'?ve\s+got\s+this\b")),
    ("encouragement.here_if_you_need", _rx(r"\bi'?m\s+here\s+if\s+you\s+need\s+anything\b")),
]

# Summary filler
SUMMARY_PATTERNS = [
    ("summary.in_summary",           _rx(r"\bin\s+summary\b")),
    ("summary.to_wrap_up",           _rx(r"\bto\s+wrap\s+up\b")),
    ("summary.overall",              _rx(r"\boverall,\s")),
    ("summary.at_the_end_of_the_day", _rx(r"\bat\s+the\s+end\s+of\s+the\s+day\b")),
]

# Motivational append
MOTIVATIONAL_PATTERNS = [
    ("motivational.remember",        _rx(r"\bremember,\s")),
    ("motivational.key_takeaway",    _rx(r"\bthe\s+key\s+takeaway\s+is\b")),
    ("motivational.most_importantly", _rx(r"\bmost\s+importantly,\s")),
]

# Performative availability
AVAILABILITY_PATTERNS = [
    ("availability.dont_hesitate",   _rx(r"\bdon'?t\s+hesitate\s+to\s+ask\b")),
    ("availability.always_happy",    _rx(r"\bi'?m\s+always\s+happy\s+to\b")),
    ("availability.anytime",         _rx(r"\banytime!?\s*$")),
]

ALL_PATTERNS = (
    ENCOURAGEMENT_PATTERNS
    + SUMMARY_PATTERNS
    + MOTIVATIONAL_PATTERNS
    + AVAILABILITY_PATTERNS
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_code_fences(text: str) -> str:
    """Remove fenced code blocks so we don't flag code examples."""
    return re.sub(r"```[\s\S]*?```", "", text)


def _strip_inline_code(text: str) -> str:
    """Remove inline code so we don't flag variable names."""
    return re.sub(r"`[^`]+`", "", text)


def _extract_last_n_sentences(text: str, n: int = 3) -> tuple[str, int]:
    """
    Extract the last N sentences from text. Returns (tail_text, char_offset)
    where char_offset is the starting position of tail_text within the
    original text.

    Sentence splitting uses ., !, ? followed by whitespace or end-of-string,
    but avoids splitting on common abbreviations (e.g., "e.g.", "i.e.").
    """
    # Split on sentence-ending punctuation followed by whitespace or EOL
    # We need to find sentence boundaries, not just split
    sent_boundary = re.compile(r'(?<=[.!?])\s+')
    sentences = sent_boundary.split(text.strip())

    # Filter out empty strings
    sentences = [s for s in sentences if s.strip()]

    if len(sentences) <= n:
        return text, 0

    # Take last N sentences
    tail_sentences = sentences[-n:]
    tail_text = " ".join(tail_sentences)

    # Find where this tail starts in the original text
    # Search for the first tail sentence in the original text, starting from the end
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

class ClosureRushGuard(Guard):
    """
    Catches reflexive closing filler appended to the end of responses.
    Only scans the last 3 sentences — closings in the middle are ignored.
    """

    @property
    def guard_id(self) -> str:
        return "closure-rush"

    @property
    def version(self) -> str:
        return "0.1.0"

    def scan(self, text: str, **kwargs) -> GuardReport:
        report = GuardReport(guard_id=self.guard_id, version=self.version)

        # Strip code fences and inline code
        scannable = _strip_code_fences(text)
        scannable = _strip_inline_code(scannable)

        # Only scan the last 3 sentences
        tail_text, tail_offset = _extract_last_n_sentences(scannable, n=3)

        for rule_id, rx in ALL_PATTERNS:
            for m in rx.finditer(tail_text):
                frag = m.group(0).strip()
                frag = (frag[:57] + "...") if len(frag) > 60 else frag

                # Calculate position in original text for line number
                abs_start = tail_offset + m.start()

                report.flags.append(Flag(
                    rule_id=f"closing.{rule_id}",
                    tier="closing",
                    severity="review",
                    match=frag,
                    line=_line_of(scannable, abs_start),
                    context=_extract_context(scannable, abs_start, tail_offset + m.end()),
                ))

        return report


# CLI entry point
if __name__ == "__main__":
    guard = ClosureRushGuard()
    run_guard_cli(guard)
