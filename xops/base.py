"""
base.py — xOP interface for the framework.

An xOP is a judgment engine. Guards find candidates; xOPs decide whether
the candidate is actually a problem.

Two xOP types:
  Resolution xOP: artifact + Guard findings -> keep | delete | replace | abstain
  Evaluation xOP: interaction trace -> behavioral state | abstain

The xOP itself is a markdown specification — the judgment is executed by
an LLM agent governed by that spec. This module defines the data structures
and enforces construction-time invariants so invalid states cannot be
represented.

v0.2.0 — hardened contracts, fail-closed defaults, two xOP types.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional, List


# ---------------------------------------------------------------------------
# Closed enumerations — these are the ONLY valid values
# ---------------------------------------------------------------------------
VALID_DISPOSITIONS = frozenset({"keep", "delete", "replace", "abstain"})
VALID_CONFIDENCE = frozenset({"high", "medium", "low"})
VALID_REVIEWERS = frozenset({"model", "human", "rule", "adjudicator"})
VALID_GATE_STATUS = frozenset({"not_evaluated", "held", "violated", "inconclusive"})
VALID_FALLBACK_ACTIONS = frozenset({"preserve_original", "suggest_alternative", "human_review"})
VALID_XOP_TYPES = frozenset({"resolution", "evaluation"})
VALID_SCOPES = frozenset({"flag", "artifact", "conversation"})


# ---------------------------------------------------------------------------
# Resolution xOP output
# ---------------------------------------------------------------------------
@dataclass
class Disposition:
    """
    A single judgment on a Guard flag. Used by Resolution xOPs.

    Construction-time invariants:
      - replace requires non-empty replacement text
      - keep and delete forbid replacement text
      - abstain forbids replacement text and requires fallback_action
      - fallback_action is only valid for abstain
      - empty flag_ref, branch, or warrant are invalid
      - all enum fields are validated against closed sets
    """
    flag_ref: str              # "vocabulary.delve@L12" — links back to the Guard flag
    disposition: str           # "keep" | "delete" | "replace" | "abstain"
    branch: str                # which fork branch was taken
    warrant: str               # WHY this disposition — the reasoning
    confidence: str = "high"   # "high" | "medium" | "low"
    replacement: str = ""      # replacement text — ONLY valid when disposition=replace
    fallback_action: str = ""  # ONLY for abstain: "preserve_original" | "suggest_alternative" | "human_review"
    reviewer: str = "model"    # "model" | "human" | "rule" | "adjudicator"
    evidence_spans: list = field(default_factory=list)  # source text spans backing the warrant

    def __post_init__(self):
        """Validate invariants at construction time. Fail-closed."""
        # --- Required fields ---
        if not self.flag_ref or not self.flag_ref.strip():
            raise ValueError("Disposition.flag_ref cannot be empty")
        if not self.branch or not self.branch.strip():
            raise ValueError("Disposition.branch cannot be empty")
        if not self.warrant or not self.warrant.strip():
            raise ValueError("Disposition.warrant cannot be empty")

        # --- Closed enumerations ---
        if self.disposition not in VALID_DISPOSITIONS:
            raise ValueError(
                f"Disposition.disposition must be one of {sorted(VALID_DISPOSITIONS)}, "
                f"got '{self.disposition}'"
            )
        if self.confidence not in VALID_CONFIDENCE:
            raise ValueError(
                f"Disposition.confidence must be one of {sorted(VALID_CONFIDENCE)}, "
                f"got '{self.confidence}'"
            )
        if self.reviewer not in VALID_REVIEWERS:
            raise ValueError(
                f"Disposition.reviewer must be one of {sorted(VALID_REVIEWERS)}, "
                f"got '{self.reviewer}'"
            )

        # --- Cross-field invariants ---
        if self.disposition == "replace" and not self.replacement:
            raise ValueError(
                "disposition='replace' requires non-empty replacement text"
            )
        if self.disposition in ("keep", "delete") and self.replacement:
            raise ValueError(
                f"disposition='{self.disposition}' forbids replacement text"
            )
        if self.disposition == "abstain" and self.replacement:
            raise ValueError(
                "disposition='abstain' forbids replacement text — "
                "an unresolved judgment cannot silently edit"
            )
        if self.disposition == "abstain" and not self.fallback_action:
            raise ValueError(
                "disposition='abstain' requires a fallback_action "
                "(preserve_original | suggest_alternative | human_review)"
            )
        if self.disposition != "abstain" and self.fallback_action:
            raise ValueError(
                f"fallback_action is only valid for disposition='abstain', "
                f"got disposition='{self.disposition}'"
            )
        if self.fallback_action and self.fallback_action not in VALID_FALLBACK_ACTIONS:
            raise ValueError(
                f"fallback_action must be one of {sorted(VALID_FALLBACK_ACTIONS)}, "
                f"got '{self.fallback_action}'"
            )


# ---------------------------------------------------------------------------
# Evaluation xOP output
# ---------------------------------------------------------------------------
@dataclass
class EvaluationFinding:
    """
    A behavioral state assessment. Used by Evaluation xOPs.

    Unlike Disposition, this does not produce text edits. It classifies
    behavioral state over an interaction trace.
    """
    finding_ref: str           # reference ID for the finding
    state: str                 # domain-specific state (e.g., "warranted_persistence")
    warrant: str               # WHY this state was assessed
    confidence: str = "high"   # "high" | "medium" | "low"
    reviewer: str = "model"    # "model" | "human" | "rule" | "adjudicator"
    evidence_spans: list = field(default_factory=list)  # conversation spans backing the warrant

    def __post_init__(self):
        if not self.finding_ref or not self.finding_ref.strip():
            raise ValueError("EvaluationFinding.finding_ref cannot be empty")
        if not self.state or not self.state.strip():
            raise ValueError("EvaluationFinding.state cannot be empty")
        if not self.warrant or not self.warrant.strip():
            raise ValueError("EvaluationFinding.warrant cannot be empty")
        if self.confidence not in VALID_CONFIDENCE:
            raise ValueError(
                f"confidence must be one of {sorted(VALID_CONFIDENCE)}, "
                f"got '{self.confidence}'"
            )
        if self.reviewer not in VALID_REVIEWERS:
            raise ValueError(
                f"reviewer must be one of {sorted(VALID_REVIEWERS)}, "
                f"got '{self.reviewer}'"
            )


# ---------------------------------------------------------------------------
# xOP Report
# ---------------------------------------------------------------------------
@dataclass
class XopReport:
    """
    Standard output from an xOP judgment pass.

    Key invariants:
      - gate_status defaults to "not_evaluated" (never to "held")
      - resolution xOPs produce dispositions, evaluation xOPs produce findings
      - disposition_counts is derived, not independently supplied
    """
    xop_id: str
    version: str
    xop_type: str = "resolution"        # "resolution" | "evaluation"
    scope: str = "flag"                  # "flag" | "artifact" | "conversation"
    dispositions: list = field(default_factory=list)   # List[Disposition] — resolution
    findings: list = field(default_factory=list)        # List[EvaluationFinding] — evaluation
    gate_status: str = "not_evaluated"   # NEVER defaults to "held"
    gate_violations: list = field(default_factory=list)
    run_id: str = ""
    input_hash: str = ""
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.xop_id or not self.xop_id.strip():
            raise ValueError("XopReport.xop_id cannot be empty")
        if not self.version or not self.version.strip():
            raise ValueError("XopReport.version cannot be empty")
        if self.xop_type not in VALID_XOP_TYPES:
            raise ValueError(
                f"xop_type must be one of {sorted(VALID_XOP_TYPES)}, "
                f"got '{self.xop_type}'"
            )
        if self.scope not in VALID_SCOPES:
            raise ValueError(
                f"scope must be one of {sorted(VALID_SCOPES)}, "
                f"got '{self.scope}'"
            )
        if self.gate_status not in VALID_GATE_STATUS:
            raise ValueError(
                f"gate_status must be one of {sorted(VALID_GATE_STATUS)}, "
                f"got '{self.gate_status}'"
            )
        # Type-content consistency
        if self.xop_type == "resolution" and self.findings:
            raise ValueError("Resolution xOP should use dispositions, not findings")
        if self.xop_type == "evaluation" and self.dispositions:
            raise ValueError("Evaluation xOP should use findings, not dispositions")
        # Auto-generate run_id
        if not self.run_id:
            self.run_id = uuid.uuid4().hex[:8]

    def to_dict(self) -> dict:
        d = {
            "xop_id": self.xop_id,
            "version": self.version,
            "xop_type": self.xop_type,
            "scope": self.scope,
            "gate_status": self.gate_status,
            "gate_violations": self.gate_violations,
            "run_id": self.run_id,
            "input_hash": self.input_hash,
            "metadata": self.metadata,
        }
        if self.xop_type == "resolution":
            d["dispositions"] = [asdict(disp) for disp in self.dispositions]
            d["disposition_counts"] = self.disposition_counts
        else:
            d["findings"] = [asdict(f) for f in self.findings]
        return d

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    # --- Derived properties (resolution xOPs) ---

    @property
    def keeps(self) -> list:
        return [d for d in self.dispositions if d.disposition == "keep"]

    @property
    def replacements(self) -> list:
        return [d for d in self.dispositions if d.disposition == "replace"]

    @property
    def deletions(self) -> list:
        return [d for d in self.dispositions if d.disposition == "delete"]

    @property
    def abstentions(self) -> list:
        return [d for d in self.dispositions if d.disposition == "abstain"]

    @property
    def disposition_counts(self) -> dict:
        """Derived from dispositions — never independently supplied."""
        counts = {}
        for d in self.dispositions:
            counts[d.disposition] = counts.get(d.disposition, 0) + 1
        return counts


# ---------------------------------------------------------------------------
# Resolution Report — final output after Guards + xOPs + Resolution
# ---------------------------------------------------------------------------
@dataclass
class ResolutionReport:
    """
    Final aggregated output after Guards + xOPs + Resolution.

    Key invariants:
      - disposition_counts is derived from xop_reports
      - gates_held is derived from xop_reports
      - these are NEVER independently supplied fields that can disagree
    """
    run_id: str = ""
    input_hash: str = ""
    artifact_id: str = ""
    guards_run: list = field(default_factory=list)   # [{guard_id, version}]
    xops_run: list = field(default_factory=list)      # [{xop_id, version, xop_type}]
    total_flags: int = 0
    xop_reports: list = field(default_factory=list)   # List[XopReport]
    resolved_text: str = ""
    audit: list = field(default_factory=list)

    def __post_init__(self):
        if not self.run_id:
            self.run_id = uuid.uuid4().hex[:8]

    # --- All counts and status are DERIVED, not stored ---

    @property
    def disposition_counts(self) -> dict:
        """Derived from xOP reports. Never independently supplied."""
        counts = {}
        for report in self.xop_reports:
            if report.xop_type == "resolution":
                for d in report.dispositions:
                    counts[d.disposition] = counts.get(d.disposition, 0) + 1
        return counts

    @property
    def gates_held(self) -> bool:
        """
        Derived from xOP reports. True only if ALL evaluated gates held.
        Not-evaluated gates do not count as failures.
        """
        evaluated = [r for r in self.xop_reports
                     if r.gate_status != "not_evaluated"]
        if not evaluated:
            return True  # No gates evaluated — not a failure, just not measured
        return all(r.gate_status == "held" for r in evaluated)

    @property
    def gate_summary(self) -> str:
        """Human-readable gate status."""
        evaluated = [r for r in self.xop_reports
                     if r.gate_status != "not_evaluated"]
        if not evaluated:
            return "no gates evaluated"
        violations = [r for r in evaluated if r.gate_status == "violated"]
        if violations:
            ids = [r.xop_id for r in violations]
            return f"GATE VIOLATION in {', '.join(ids)}"
        inconclusive = [r for r in evaluated if r.gate_status == "inconclusive"]
        if inconclusive:
            ids = [r.xop_id for r in inconclusive]
            held = len(evaluated) - len(inconclusive)
            return f"{held} gates held, {len(inconclusive)} inconclusive ({', '.join(ids)})"
        return f"all {len(evaluated)} gates held"

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "input_hash": self.input_hash,
            "artifact_id": self.artifact_id,
            "guards_run": self.guards_run,
            "xops_run": self.xops_run,
            "total_flags": self.total_flags,
            "disposition_counts": self.disposition_counts,
            "gates_held": self.gates_held,
            "gate_summary": self.gate_summary,
            "xop_reports": [r.to_dict() for r in self.xop_reports],
            "resolved_text": self.resolved_text,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def summary(self) -> str:
        """One-line summary for self-check mode."""
        counts = self.disposition_counts
        parts = []
        for action in ("keep", "replace", "delete", "abstain"):
            n = counts.get(action, 0)
            if n:
                parts.append(f"{n} {action}")
        return f"QA: {self.total_flags} flags -> {', '.join(parts) or 'none'}. {self.gate_summary}."
