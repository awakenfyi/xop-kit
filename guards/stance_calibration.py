#!/usr/bin/env python3
"""
stance_calibration.py — Guard for escaped stance persistence (v0.1.0).

Catches the behavioral pattern where a model adopts a stance (refusal,
register, posture, level of caution) early in a conversation and holds it
after the prompt has moved on. The Guard scans for SURFACE SIGNALS of
stance persistence across turns — it cannot determine whether persistence
is warranted. That judgment is the xOP's job.

Input: a JSON conversation (list of {"role": "user"|"assistant", "content": ...}).
If plain text is provided instead, the Guard runs in degraded mode scanning
only for refusal echoes and caveat persistence.

All flags are severity "review" — the Guard cannot distinguish warranted
persistence from escaped persistence.

Badge: FIXTURE-TESTED.
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
# Helpers
# ---------------------------------------------------------------------------

def _rx(p):
    return re.compile(p, re.IGNORECASE)


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


def _parse_conversation(text: str):
    """
    Try to parse the input as a JSON conversation.
    Returns (messages, is_conversation).
    If parsing fails, returns (None, False).
    """
    stripped = text.strip()
    if stripped.startswith("["):
        try:
            messages = json.loads(stripped)
            if (isinstance(messages, list)
                    and len(messages) > 0
                    and isinstance(messages[0], dict)
                    and "role" in messages[0]):
                return messages, True
        except (json.JSONDecodeError, KeyError):
            pass
    return None, False


# ---------------------------------------------------------------------------
# SIGNAL DEFINITIONS
# ---------------------------------------------------------------------------

# Refusal echoes: assistant referencing a prior refusal/position
REFUSAL_ECHOES = [
    ("refusal_echo.as_i_mentioned",       _rx(r"\bas I (mentioned|noted|said|stated|explained)\b")),
    ("refusal_echo.as_i_said_before",     _rx(r"\bas I (said|mentioned|noted|stated|explained) (before|earlier|previously|above)\b")),
    ("refusal_echo.i_still_cant",         _rx(r"\bI (still )?(can'?t|cannot|am unable to|won'?t|will not)\b")),
    ("refusal_echo.still_unable",         _rx(r"\bI'?m still (unable|not able) to\b")),
    ("refusal_echo.already_explained",    _rx(r"\bI'?ve already (explained|mentioned|noted|addressed|covered)\b")),
    ("refusal_echo.previous_answer",      _rx(r"\bmy (previous|earlier|prior) (answer|response|explanation) still (applies|stands|holds)\b")),
    ("refusal_echo.as_before",            _rx(r"\bas (before|previously),?\s")),
    ("refusal_echo.i_maintain",           _rx(r"\bI (still )?(maintain|stand by)\b")),
    ("refusal_echo.reiterating",          _rx(r"\b(to reiterate|reiterating|once again)\b")),
]

# Caveat persistence: same disclaimers repeated across turns
CAVEAT_PATTERNS = [
    ("caveat.important_to_note",    _rx(r"\b(it'?s|it is) important to (note|remember|consider|keep in mind)\b")),
    ("caveat.should_mention",       _rx(r"\bI should (mention|note|point out|emphasize|stress)\b")),
    ("caveat.keep_in_mind",         _rx(r"\b(keep|bear) in mind (that|this)\b")),
    ("caveat.please_note",          _rx(r"\bplease (note|be aware|remember)\b")),
    ("caveat.disclaimer",           _rx(r"\b(however|that said),?\s*(it'?s|it is) (important|worth|crucial) to\b")),
    ("caveat.want_to_emphasize",    _rx(r"\bI (want|need) to (emphasize|stress|reiterate|underscore)\b")),
    ("caveat.important_caveat",     _rx(r"\b(an? )?important (caveat|disclaimer|note|warning)\b")),
    ("caveat.must_stress",          _rx(r"\bI must (stress|emphasize|reiterate)\b")),
]

# Scope-shift keywords in user messages that suggest topic change
SCOPE_SHIFT_PATTERNS = [
    ("scope_shift.forget_that",     _rx(r"\bforget (that|about (it|that|this))\b")),
    ("scope_shift.different",       _rx(r"\b(different|unrelated|separate|new) (question|topic|subject|thing|issue)\b")),
    ("scope_shift.actually",        _rx(r"^actually\b|^\s*actually,?\s")),
    ("scope_shift.never_mind",      _rx(r"\bnever ?mind\b")),
    ("scope_shift.new_topic",       _rx(r"\bnew topic\b")),
    ("scope_shift.separately",      _rx(r"^separately\b|^\s*separately,?\s")),
    ("scope_shift.anyway",          _rx(r"^anyway\b|^\s*anyway,?\s")),
    ("scope_shift.moving_on",       _rx(r"\bmoving on\b")),
    ("scope_shift.forget_about",    _rx(r"\bforget about\b")),
    ("scope_shift.can_we_talk",     _rx(r"\bcan (we|you) (talk|help|switch|move)\b.{0,20}?\b(about|to|on)\b")),
    ("scope_shift.changing_subject", _rx(r"\bchanging (the )?subject\b")),
    ("scope_shift.something_else",  _rx(r"\bsomething (else|different)\b")),
    ("scope_shift.on_another_note", _rx(r"\bon (another|a different) (note|topic)\b")),
]


# ---------------------------------------------------------------------------
# Register-lock detection
# ---------------------------------------------------------------------------

def _estimate_formality(text: str) -> float:
    """
    Crude formality score. Higher = more formal. Range roughly 0-1.
    Uses signal words and structural markers — not judgment, just counting.
    """
    if not text.strip():
        return 0.5

    words = text.lower().split()
    word_count = max(len(words), 1)

    formal_markers = [
        "therefore", "furthermore", "moreover", "consequently",
        "nevertheless", "notwithstanding", "regarding", "pertaining",
        "accordingly", "henceforth", "aforementioned", "herein",
        "pursuant", "shall", "whom", "hence",
    ]
    informal_markers = [
        "hey", "yeah", "yep", "nah", "gonna", "wanna", "gotta",
        "lol", "ok", "okay", "cool", "sure", "btw", "fyi",
        "haha", "hmm", "ugh", "whoa", "wow", "dude", "bro",
    ]

    formal_count = sum(1 for w in words if w.rstrip(".,!?;:") in formal_markers)
    informal_count = sum(1 for w in words if w.rstrip(".,!?;:") in informal_markers)

    # Average sentence length (longer = more formal, roughly)
    sentences = re.split(r'[.!?]+', text)
    sentences = [s for s in sentences if s.strip()]
    avg_sent_len = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
    length_signal = min(avg_sent_len / 30.0, 1.0)  # normalize to ~0-1

    # Contractions signal informality
    contraction_count = len(re.findall(r"\b\w+'(?:t|re|ve|ll|d|s|m)\b", text, re.IGNORECASE))

    score = 0.5
    score += (formal_count / word_count) * 3.0
    score -= (informal_count / word_count) * 3.0
    score += length_signal * 0.2
    score -= (contraction_count / word_count) * 1.5

    return max(0.0, min(1.0, score))


def _detect_register_lock(messages: list) -> list:
    """
    Detect if assistant register stays constant across 3+ turns
    while user register shifts.

    Returns list of flags (or empty).
    """
    # Need at least 3 assistant turns to check register lock
    assistant_turns = [(i, m) for i, m in enumerate(messages) if m["role"] == "assistant"]
    user_turns = [(i, m) for i, m in enumerate(messages) if m["role"] == "user"]

    if len(assistant_turns) < 3 or len(user_turns) < 2:
        return []

    # Compute formality scores
    user_scores = [_estimate_formality(m["content"]) for _, m in user_turns]
    asst_scores = [_estimate_formality(m["content"]) for _, m in assistant_turns]

    # Check if user register shifted significantly
    user_range = max(user_scores) - min(user_scores)
    if user_range < 0.15:
        # User register is stable — no shift to detect
        return []

    # Check if last 3 assistant turns are within a narrow band
    last_3_asst = asst_scores[-3:]
    asst_range = max(last_3_asst) - min(last_3_asst)

    if asst_range < 0.08:
        # Assistant register is locked despite user shift
        # Also verify that user's latest register differs from assistant's
        latest_user_score = user_scores[-1]
        latest_asst_score = asst_scores[-1]
        if abs(latest_user_score - latest_asst_score) > 0.15:
            last_asst_content = assistant_turns[-1][1]["content"]
            return [Flag(
                rule_id="register_lock.formality_mismatch",
                tier="register",
                severity="review",
                match=f"assistant formality stable ({last_3_asst[-1]:.2f}) vs user shift ({user_range:.2f})",
                line=1,
                context=last_asst_content[:120],
            )]

    return []


# ---------------------------------------------------------------------------
# Guard implementation
# ---------------------------------------------------------------------------

class StanceCalibrationGuard(Guard):
    """
    Deterministic Guard for escaped stance persistence.

    In conversation mode (JSON input): scans for refusal echoes, caveat
    persistence, register lock, and scope-shift correlation in the last
    assistant turn.

    In plain-text mode (degraded): scans for refusal echoes and caveat
    persistence only.
    """

    @property
    def guard_id(self) -> str:
        return "stance-calibration"

    @property
    def version(self) -> str:
        return "0.1.0"

    def scan(self, text: str, **kwargs) -> GuardReport:
        report = GuardReport(guard_id=self.guard_id, version=self.version)

        messages, is_conversation = _parse_conversation(text)

        if is_conversation:
            self._scan_conversation(messages, report)
        else:
            self._scan_plain_text(text, report)

        return report

    def _scan_plain_text(self, text: str, report: GuardReport):
        """Degraded mode: scan plain text for refusal echoes and caveat persistence."""
        report.advisory["mode"] = "degraded_plain_text"

        for rule_id, rx in REFUSAL_ECHOES:
            for m in rx.finditer(text):
                frag = m.group(0).strip()
                report.flags.append(Flag(
                    rule_id=f"persistence.{rule_id}",
                    tier="persistence",
                    severity="review",
                    match=frag,
                    line=_line_of(text, m.start()),
                    context=_extract_context(text, m.start(), m.end()),
                ))

        for rule_id, rx in CAVEAT_PATTERNS:
            for m in rx.finditer(text):
                frag = m.group(0).strip()
                report.flags.append(Flag(
                    rule_id=f"persistence.{rule_id}",
                    tier="persistence",
                    severity="review",
                    match=frag,
                    line=_line_of(text, m.start()),
                    context=_extract_context(text, m.start(), m.end()),
                ))

    def _scan_conversation(self, messages: list, report: GuardReport):
        """Full mode: scan conversation for stance persistence + scope shifts."""
        report.advisory["mode"] = "conversation"
        report.advisory["turn_count"] = len(messages)

        # Get the last assistant message and last user message
        last_assistant = None
        last_user = None
        for m in reversed(messages):
            if m["role"] == "assistant" and last_assistant is None:
                last_assistant = m["content"]
            if m["role"] == "user" and last_user is None:
                last_user = m["content"]
            if last_assistant and last_user:
                break

        if not last_assistant:
            return

        # --- Phase 1: Scan last assistant message for persistence signals ---
        persistence_flags = []

        for rule_id, rx in REFUSAL_ECHOES:
            for m in rx.finditer(last_assistant):
                frag = m.group(0).strip()
                persistence_flags.append(Flag(
                    rule_id=f"persistence.{rule_id}",
                    tier="persistence",
                    severity="review",
                    match=frag,
                    line=_line_of(last_assistant, m.start()),
                    context=_extract_context(last_assistant, m.start(), m.end()),
                ))

        # Caveat persistence: check if the same caveat pattern appears in
        # multiple assistant turns (not just the last one)
        assistant_contents = [m["content"] for m in messages if m["role"] == "assistant"]
        if len(assistant_contents) >= 2:
            for rule_id, rx in CAVEAT_PATTERNS:
                # Count how many assistant turns contain this caveat
                turns_with_caveat = sum(
                    1 for content in assistant_contents if rx.search(content)
                )
                if turns_with_caveat >= 2:
                    # Caveat repeated across turns — flag in the last message
                    match_in_last = rx.search(last_assistant)
                    if match_in_last:
                        frag = match_in_last.group(0).strip()
                        persistence_flags.append(Flag(
                            rule_id=f"persistence.{rule_id}",
                            tier="persistence",
                            severity="review",
                            match=f"{frag} (repeated in {turns_with_caveat} turns)",
                            line=_line_of(last_assistant, match_in_last.start()),
                            context=_extract_context(
                                last_assistant, match_in_last.start(), match_in_last.end()
                            ),
                        ))

        # --- Phase 2: Scan last user message for scope-shift signals ---
        scope_shift_flags = []
        if last_user:
            for rule_id, rx in SCOPE_SHIFT_PATTERNS:
                for m in rx.finditer(last_user):
                    frag = m.group(0).strip()
                    scope_shift_flags.append(Flag(
                        rule_id=f"scope.{rule_id}",
                        tier="scope",
                        severity="review",
                        match=frag,
                        line=_line_of(last_user, m.start()),
                        context=_extract_context(last_user, m.start(), m.end()),
                    ))

        # --- Phase 3: Register lock detection ---
        register_flags = _detect_register_lock(messages)

        # --- Phase 4: Correlation ---
        # A flag is raised when: persistence signal + scope-shift keyword
        # in the same turn pair. Or register lock (which is a standalone signal).
        report.advisory["persistence_signals"] = len(persistence_flags)
        report.advisory["scope_shift_signals"] = len(scope_shift_flags)
        report.advisory["register_lock"] = len(register_flags) > 0

        if persistence_flags and scope_shift_flags:
            # Both present: emit all persistence flags (correlated with scope shift)
            for f in persistence_flags:
                f.context = f"{f.context} [scope-shift detected in user turn]"
            report.flags.extend(persistence_flags)
            # Also include scope shift flags for visibility
            report.flags.extend(scope_shift_flags)
        elif persistence_flags and not scope_shift_flags:
            # Persistence signals without scope shift — lower concern,
            # but still flag if there are refusal echoes (they're notable
            # on their own because they reference prior conversation state)
            refusal_only = [f for f in persistence_flags if "refusal_echo" in f.rule_id]
            report.flags.extend(refusal_only)
        # Scope shift alone without persistence is not flagged — the model
        # may have naturally adapted.

        # Register lock is always flagged (it's its own correlated signal)
        report.flags.extend(register_flags)


# CLI entry point
if __name__ == "__main__":
    guard = StanceCalibrationGuard()
    run_guard_cli(guard)
