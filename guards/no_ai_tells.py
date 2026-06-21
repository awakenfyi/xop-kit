#!/usr/bin/env python3
"""
no_ai_tells.py — the de-slop Guard (v0.2.0).

A DETERMINISTIC scanner for the generic-LLM voice ("AI slop"). It flags the
recurring tells that make text read as machine-written: reflexive vocabulary,
boilerplate constructions, and (advisory only) rhythm signatures.

What this is and is NOT
-----------------------
- This is a GUARD, not an xOP. It checks a mechanical rule: does the text
  contain known tells? No judgment, no model, no pilot.
- It flags CANDIDATES. It does NOT certify that text is "human" or that it
  will "beat an AI detector." Those are unprovable claims against a moving
  target and this Guard makes neither.
- A flagged word can be the right word. `delve` is sometimes correct. The
  Guard catches every instance; the paired xOP (writing-license) decides
  whether THIS instance is warranted. The Guard without the xOP will flatten
  voice — that is the documented failure mode, documented on purpose.

Fixes in v0.2.0:
  1. `Ultimately,` regex — removed trailing \\b after comma.
  2. Line numbers for newline-anchored constructions — offset corrected.
  3. Three-outcome verdicts: PASS / REVIEW / FAIL.
  4. Context extraction — each flag includes the surrounding sentence.
  5. Code fence exclusion — skips content inside ``` blocks.
  6. Deduplication — overlapping matches collapsed to longest match.

Badge: RULE-TESTED (15 fixtures). Vocabulary + construction tiers.
Rhythm tier is ADVISORY — reported, never gating.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Import from framework
sys.path.insert(0, str(Path(__file__).parent.parent))
from guards.base import Guard, GuardReport, Flag, run_guard_cli


# ---------------------------------------------------------------------------
# TIER 1 — VOCABULARY tells (review severity by default)
# ---------------------------------------------------------------------------
VOCAB_TELLS = [
    "delve", "delving", "tapestry", "realm", "boasts", "boasting",
    "treasure trove", "bustling", "ever-evolving", "ever-changing",
    "fast-paced", "cutting-edge", "game-changer", "game-changing",
    "unlock", "unlocking", "unleash", "unleashing", "elevate", "elevating",
    "seamless", "seamlessly", "robust", "leverage", "leveraging",
    "navigating the complexities", "navigate the complexities",
    "in today's world", "in today's digital", "in the world of",
    "when it comes to", "at the end of the day", "needless to say",
    "it's worth noting", "it is worth noting", "it's important to note",
    "testament to", "a testament", "rich tapestry", "vibrant",
    "underscores", "underscore", "underscoring", "pivotal", "crucial",
    "moreover", "furthermore", "notably", "indeed", "essentially",
    "meticulous", "meticulously", "plethora", "myriad", "embark",
    "foster", "fostering", "holistic", "paradigm", "synergy", "synergize",
]

# ---------------------------------------------------------------------------
# TIER 2 — CONSTRUCTION tells (sentence shapes)
# ---------------------------------------------------------------------------
def _rx(p): return re.compile(p, re.IGNORECASE)

CONSTRUCTION_TELLS = [
    ("not_just_but",        _rx(r"\bnot just\b.{0,60}?,\s*(it'?s|it is|they'?re|that'?s)\b")),
    ("not_only_but_also",   _rx(r"\bnot only\b.{0,80}?\bbut also\b")),
    ("isnt_about_its_about",_rx(r"\b(is|isn'?t|was|wasn'?t)\s+about\b.{0,60}?\.\s*(it'?s|it is)\s+about\b")),
    ("heres_the_thing",     _rx(r"\bhere'?s the thing\b")),
    ("lets_dive_in",        _rx(r"\b(let'?s|let us)\s+(dive|jump)\s+(in|into)\b|\bdiving\s+(in|into)\b")),
    ("i_hope_this_helps",   _rx(r"\bi hope (this|that) helps\b")),
    ("hope_you_find",       _rx(r"\bhope you (find|enjoy)\b")),
    ("in_conclusion",       _rx(r"(^|\n)\s*(in conclusion|in summary|to sum up|to summarize)\b")),
    # FIX: removed \b after comma — word boundary doesn't fire before space.
    # Now uses lookahead for whitespace or end-of-string.
    ("ultimately_opener",   _rx(r"(^|\n)\s*ultimately,(?=\s|$)")),
    ("whether_youre",       _rx(r"\bwhether you'?re\b.{0,60}?\bor\b")),
    ("from_x_to_y_opener",  _rx(r"(^|\n)\s*from\b.{0,40}?\bto\b.{0,40}?,")),
    ("dynamic_duo_filler",  _rx(r"\bworld of\b.{0,30}?\b(possibilities|opportunities)\b")),
    ("more_than_just",      _rx(r"\bmore than just\b")),
    ("look_no_further",     _rx(r"\blook no further\b")),
    ("rest_assured",        _rx(r"\brest assured\b")),
    ("that_being_said",     _rx(r"\bthat being said\b|\bwith that said\b")),
]

# ---------------------------------------------------------------------------
# TIER 3 — RHYTHM signals (advisory only)
# ---------------------------------------------------------------------------
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
_TRICOLON   = re.compile(r"\b[\w'-]+,\s+[\w'-]+,?\s+and\s+[\w'-]+\b", re.IGNORECASE)


def _strip_code_fences(text: str) -> str:
    """Remove fenced code blocks so we don't flag code examples."""
    return re.sub(r"```[\s\S]*?```", "", text)


def _strip_inline_code(text: str) -> str:
    """Remove inline code so we don't flag variable names."""
    return re.sub(r"`[^`]+`", "", text)


def _line_of(text: str, idx: int) -> int:
    """1-based line number for a character index."""
    return text.count("\n", 0, idx) + 1


def _line_of_content(text: str, match: re.Match) -> int:
    """
    Line number for the actual content of a match, not the preceding newline.
    FIX: for newline-anchored patterns, skip past the newline to count
    from the content start.
    """
    start = match.start()
    matched = match.group(0)

    # If match starts with newline + whitespace, find the actual content
    content_offset = 0
    for ch in matched:
        if ch in ('\n', ' ', '\t'):
            content_offset += 1
        else:
            break

    return text.count("\n", 0, start + content_offset) + 1


def _extract_context(text: str, start: int, end: int) -> str:
    """Extract the sentence surrounding a match for xOP judgment."""
    # Walk backward to sentence boundary or line start
    ctx_start = start
    while ctx_start > 0 and text[ctx_start - 1] not in '.!?\n':
        ctx_start -= 1

    # Walk forward to sentence boundary or line end
    ctx_end = end
    while ctx_end < len(text) and text[ctx_end] not in '.!?\n':
        ctx_end += 1

    return text[ctx_start:ctx_end].strip()


def _dedup_flags(flags: list) -> list:
    """
    Remove overlapping flags — keep the longest match when two flags
    cover the same text span (e.g. "rich tapestry" and "tapestry").
    """
    if not flags:
        return flags

    # Sort by line, then by match length descending
    sorted_flags = sorted(flags, key=lambda f: (f.line, -len(f.match)))
    result = []

    for flag in sorted_flags:
        # Check if this flag's match is a substring of an already-kept flag on the same line
        subsumed = False
        for kept in result:
            if kept.line == flag.line and flag.match in kept.match:
                subsumed = True
                break
        if not subsumed:
            result.append(flag)

    return result


class NoAiTellsGuard(Guard):
    """The de-slop Guard. Deterministic scanner for generic LLM voice."""

    @property
    def guard_id(self) -> str:
        return "no-ai-tells"

    @property
    def version(self) -> str:
        return "0.2.0"

    def __init__(self, extra_vocab=None, deny_rules=None):
        """
        Args:
            extra_vocab: Additional vocabulary terms to scan for.
            deny_rules: Set of rule_ids that should be severity "deny" instead
                        of "review". For house-style enforcement.
        """
        self.extra_vocab = list(extra_vocab or [])
        self.deny_rules = set(deny_rules or [])

    def scan(self, text: str, **kwargs) -> GuardReport:
        report = GuardReport(guard_id=self.guard_id, version=self.version)

        # Strip code fences and inline code before scanning
        scannable = _strip_code_fences(text)
        scannable = _strip_inline_code(scannable)

        vocab = VOCAB_TELLS + self.extra_vocab

        # Tier 1 — vocabulary
        for term in vocab:
            pattern = r"\b" + re.escape(term) + r"\b"
            for m in re.finditer(pattern, scannable, re.IGNORECASE):
                rule_id = f"vocabulary.{term.lower().replace(' ', '_')}"
                severity = "deny" if rule_id in self.deny_rules else "review"
                report.flags.append(Flag(
                    rule_id=rule_id,
                    tier="vocabulary",
                    severity=severity,
                    match=m.group(0),
                    line=_line_of(scannable, m.start()),
                    context=_extract_context(scannable, m.start(), m.end()),
                ))

        # Tier 2 — construction
        for name, rx in CONSTRUCTION_TELLS:
            for m in rx.finditer(scannable):
                frag = m.group(0).strip().replace("\n", " ")
                frag = (frag[:57] + "...") if len(frag) > 60 else frag
                rule_id = f"construction.{name}"
                severity = "deny" if rule_id in self.deny_rules else "review"
                report.flags.append(Flag(
                    rule_id=rule_id,
                    tier="construction",
                    severity=severity,
                    match=frag,
                    line=_line_of_content(scannable, m),
                    context=_extract_context(scannable, m.start(), m.end()),
                ))

        # Dedup overlapping flags
        report.flags = _dedup_flags(report.flags)

        # Tier 3 — rhythm (advisory, never gating)
        words = re.findall(r"\b[\w'-]+\b", scannable)
        sents = [s for s in _SENT_SPLIT.split(scannable.strip()) if s.strip()]
        lens = [len(re.findall(r"\b[\w'-]+\b", s)) for s in sents] or [0]
        mean = sum(lens) / len(lens)
        var = sum((l - mean) ** 2 for l in lens) / len(lens)

        report.advisory = {
            "word_count": len(words),
            "sentence_count": len(sents),
            "mean_sentence_len": round(mean, 1),
            "sentence_len_stdev": round(var ** 0.5, 1),
            "em_dashes_per_1k_words": round(1000 * text.count("—") / max(len(words), 1), 1),
            "tricolon_count": len(_TRICOLON.findall(scannable)),
        }

        return report


# CLI entry point
if __name__ == "__main__":
    guard = NoAiTellsGuard()
    run_guard_cli(guard)
