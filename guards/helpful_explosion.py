#!/usr/bin/env python3
"""
helpful_explosion.py — Guard for the "helpful explosion" pattern (v0.1.0).

Detects when a model over-serves: exhaustive lists, walls of text, excessive
structure, enumeration openers — all in response to questions that didn't
ask for it.

This is a STRUCTURAL scanner. It counts bullets, headers, sections, and
words. It does not judge vocabulary.

Tiers:
  - structure: excessive bullets, headers, multiple numbered lists
  - construction: enumeration openers ("Here are 10 ways...")
  - rhythm (advisory): word count threshold (not gating — some long
    responses are warranted)

All hard flags are severity "review" because some long responses are
legitimate. The xOP decides whether to trim.

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
# Helpers
# ---------------------------------------------------------------------------

def _strip_code_fences(text: str) -> str:
    """Blank out fenced code blocks so we don't flag code structure.

    Replaces non-newline characters with spaces rather than deleting them so
    that character offsets and line numbers remain valid for subsequent callers
    such as _line_of() and _extract_context().
    """
    return re.sub(r"```[\s\S]*?```", lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)


def _line_of(text: str, idx: int) -> int:
    """1-based line number for a character index."""
    return text.count("\n", 0, idx) + 1


def _extract_context(text: str, start: int, end: int) -> str:
    """Extract surrounding sentence for xOP judgment."""
    ctx_start = start
    while ctx_start > 0 and text[ctx_start - 1] not in '.!?\n':
        ctx_start -= 1
    ctx_end = end
    while ctx_end < len(text) and text[ctx_end] not in '.!?\n':
        ctx_end += 1
    return text[ctx_start:ctx_end].strip()


# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

# Bullet/numbered list item patterns
_BULLET_RE = re.compile(r"^[ \t]*[-*+][ \t]+\S", re.MULTILINE)
_NUMBERED_RE = re.compile(r"^[ \t]*\d+[.)]\s+\S", re.MULTILINE)

# Header patterns (## or ### — we count markdown headers)
_HEADER_RE = re.compile(r"^#{2,6}\s+\S", re.MULTILINE)

# Enumeration opener: "Here are X ways/tips/strategies/things/reasons/steps/methods"
_ENUM_OPENER_RE = re.compile(
    r"\bhere\s+are\s+(\d+|several|some|many|a\s+few|numerous|various)\s+"
    r"(ways|tips|strategies|things|reasons|steps|methods|techniques|approaches|ideas|"
    r"examples|factors|points|benefits|advantages|considerations|guidelines|best\s+practices|"
    r"key\s+takeaways|principles|insights|lessons|suggestions|recommendations)\b",
    re.IGNORECASE,
)

# Threshold constants
MAX_BULLETS = 7
MAX_HEADERS = 4
WORD_COUNT_ADVISORY = 800


class HelpfulExplosionGuard(Guard):
    """
    Structural scanner for the helpful-explosion pattern.

    Catches exhaustive lists, excessive headers, enumeration openers,
    and multiple numbered lists. Word count is advisory (not gating).
    """

    @property
    def guard_id(self) -> str:
        return "helpful-explosion"

    @property
    def version(self) -> str:
        return "0.1.0"

    def scan(self, text: str, **kwargs) -> GuardReport:
        report = GuardReport(guard_id=self.guard_id, version=self.version)

        # Strip code fences before scanning
        scannable = _strip_code_fences(text)

        # ---------------------------------------------------------------
        # TIER 1 — STRUCTURE checks (hard flags, severity "review")
        # ---------------------------------------------------------------

        # 1. Excessive bullet points (unordered)
        bullet_matches = list(_BULLET_RE.finditer(scannable))
        if len(bullet_matches) > MAX_BULLETS:
            # Flag at the position of the first bullet that exceeds threshold
            over = bullet_matches[MAX_BULLETS]
            report.flags.append(Flag(
                rule_id="structure.excessive_bullets",
                tier="structure",
                severity="review",
                match=f"{len(bullet_matches)} bullet items (threshold: {MAX_BULLETS})",
                line=_line_of(scannable, over.start()),
                context=f"Response contains {len(bullet_matches)} bullet points",
            ))

        # 2. Excessive numbered list items
        numbered_matches = list(_NUMBERED_RE.finditer(scannable))
        if len(numbered_matches) > MAX_BULLETS:
            over = numbered_matches[MAX_BULLETS]
            report.flags.append(Flag(
                rule_id="structure.excessive_numbered_items",
                tier="structure",
                severity="review",
                match=f"{len(numbered_matches)} numbered items (threshold: {MAX_BULLETS})",
                line=_line_of(scannable, over.start()),
                context=f"Response contains {len(numbered_matches)} numbered list items",
            ))

        # 3. Excessive headers
        header_matches = list(_HEADER_RE.finditer(scannable))
        if len(header_matches) > MAX_HEADERS:
            over = header_matches[MAX_HEADERS]
            report.flags.append(Flag(
                rule_id="structure.excessive_headers",
                tier="structure",
                severity="review",
                match=f"{len(header_matches)} headers (threshold: {MAX_HEADERS})",
                line=_line_of(scannable, over.start()),
                context=f"Response contains {len(header_matches)} section headers",
            ))

        # 4. Multiple numbered lists in one response
        #    Detect by finding gaps in numbered sequences (a new "1." after
        #    a higher number, or separated by non-list content).
        if numbered_matches:
            list_count = _count_numbered_lists(scannable, numbered_matches)
            if list_count > 1:
                report.flags.append(Flag(
                    rule_id="structure.multiple_numbered_lists",
                    tier="structure",
                    severity="review",
                    match=f"{list_count} separate numbered lists",
                    line=_line_of(scannable, numbered_matches[0].start()),
                    context="Response contains multiple numbered lists",
                ))

        # ---------------------------------------------------------------
        # TIER 2 — CONSTRUCTION checks (enumeration openers)
        # ---------------------------------------------------------------

        for m in _ENUM_OPENER_RE.finditer(scannable):
            frag = m.group(0).strip()
            frag = (frag[:57] + "...") if len(frag) > 60 else frag
            report.flags.append(Flag(
                rule_id="construction.enumeration_opener",
                tier="construction",
                severity="review",
                match=frag,
                line=_line_of(scannable, m.start()),
                context=_extract_context(scannable, m.start(), m.end()),
            ))

        # ---------------------------------------------------------------
        # TIER 3 — RHYTHM (advisory, never gating)
        # ---------------------------------------------------------------
        words = re.findall(r"\b[\w'-]+\b", scannable)
        word_count = len(words)

        report.advisory = {
            "word_count": word_count,
            "bullet_count": len(bullet_matches),
            "numbered_item_count": len(numbered_matches),
            "header_count": len(header_matches),
            "word_count_exceeds_advisory": word_count > WORD_COUNT_ADVISORY,
        }

        return report


def _count_numbered_lists(text: str, matches: list) -> int:
    """
    Count distinct numbered lists by detecting restarts.
    A new list starts when a numbered item begins with 1 (or when there's
    a significant gap of non-list lines between items).
    """
    if not matches:
        return 0

    lists = 1
    prev_line = _line_of(text, matches[0].start())
    prev_num = _extract_number(matches[0].group(0))

    for m in matches[1:]:
        curr_line = _line_of(text, m.start())
        curr_num = _extract_number(m.group(0))

        # A restart: number resets to 1, or there's a gap of 3+ lines
        # between items (indicating a new section).
        if curr_num == 1 and prev_num > 1:
            lists += 1
        elif curr_line - prev_line > 4 and curr_num <= prev_num:
            lists += 1

        prev_line = curr_line
        prev_num = curr_num

    return lists


def _extract_number(item_text: str) -> int:
    """Extract the number from a numbered list item like '3. foo'."""
    m = re.match(r"\s*(\d+)", item_text)
    return int(m.group(1)) if m else 0


# CLI entry point
if __name__ == "__main__":
    guard = HelpfulExplosionGuard()
    run_guard_cli(guard)
