"""
Module 11 — HELIX: Authority Boundary
========================================
Code-enforced version of the governance boundary stated in ADR 011,
following the same pattern as Module 10 (AEGIS)'s AuthorityBoundary:
the boundary is not just documentation, it's a runtime check every
routed result passes through before being surfaced to a user.

HELIX's boundary is simpler than AEGIS's tiered (Tier 0-3) authority
model, because HELIX never takes an enforcement action — it only
classifies and explains. The boundary here is narrower and specifically
about CONTENT, not action: every result and every RAG response must be
checked for language that crosses from "classification of published
data" into "diagnosis, management, or individual medical advice."

This module does not (and cannot) guarantee perfect detection of
boundary-crossing language — it is a defense-in-depth check, not a
substitute for careful prompt design in hybrid_rag.py or careful review
of new sub-model rationale strings. It exists so a boundary violation is
caught by an automated check BEFORE reaching a user, rather than relying
solely on manual review.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class BoundaryViolationSeverity(str, Enum):
    NONE = "none"
    ADVISORY = "advisory"     # borderline phrasing, flagged but not blocked
    BLOCKING = "blocking"     # must not be surfaced to a user as-is


@dataclass
class BoundaryCheckResult:
    passed: bool
    severity: BoundaryViolationSeverity
    flagged_phrases: list[str]
    notes: list[str]


# Phrases that directly instruct or address an individual as if HELIX were
# their treating clinician — these are BLOCKING. HELIX may describe what
# "management" or "diagnosis" typically involves for a disorder in the
# abstract (that's the RAG knowledge base's job), but must never phrase
# output as directed advice to the specific person reading it.
_BLOCKING_PATTERNS: list[re.Pattern] = [
    re.compile(r"\byou (should|must|need to) (take|start|stop|see a|consult)\b", re.IGNORECASE),
    re.compile(r"\byou (have|are affected by|are diagnosed with)\b", re.IGNORECASE),
    re.compile(r"\bI diagnose\b", re.IGNORECASE),
    re.compile(r"\byour (diagnosis|prognosis|treatment plan) is\b", re.IGNORECASE),
    re.compile(r"\brecommended dosage for you\b", re.IGNORECASE),
]

# Phrases that are not outright directives but lean toward individual
# medical advice framing rather than population/reference-level
# information — flagged for review, not auto-blocked, since some of
# these can appear in legitimate general-education phrasing.
_ADVISORY_PATTERNS: list[re.Pattern] = [
    re.compile(r"\byou should consider\b", re.IGNORECASE),
    re.compile(r"\bin your case\b", re.IGNORECASE),
    re.compile(r"\bthis means you\b", re.IGNORECASE),
]


def check_text_for_boundary_violations(text: str) -> BoundaryCheckResult:
    """
    Scans a single piece of output text (a RAG response, a sub-model
    rationale string, a dashboard-rendered summary) for language that
    crosses the governance boundary.
    """
    flagged: list[str] = []
    notes: list[str] = []

    blocking_hit = False
    for pattern in _BLOCKING_PATTERNS:
        match = pattern.search(text)
        if match:
            blocking_hit = True
            flagged.append(match.group(0))

    advisory_hit = False
    for pattern in _ADVISORY_PATTERNS:
        match = pattern.search(text)
        if match:
            advisory_hit = True
            flagged.append(match.group(0))

    if blocking_hit:
        notes.append(
            "Text contains directive, individually-addressed medical "
            "language — this must be rewritten before being surfaced. "
            "HELIX explains and classifies published data; it does not "
            "instruct an individual on their care."
        )
        return BoundaryCheckResult(
            passed=False,
            severity=BoundaryViolationSeverity.BLOCKING,
            flagged_phrases=flagged,
            notes=notes,
        )

    if advisory_hit:
        notes.append(
            "Text leans toward individually-directed framing — not "
            "automatically blocked, but should be reviewed before "
            "shipping as default output copy."
        )
        return BoundaryCheckResult(
            passed=True,
            severity=BoundaryViolationSeverity.ADVISORY,
            flagged_phrases=flagged,
            notes=notes,
        )

    return BoundaryCheckResult(
        passed=True,
        severity=BoundaryViolationSeverity.NONE,
        flagged_phrases=[],
        notes=["No boundary-violation language detected."],
    )


# ---------------------------------------------------------------------------
# Standing disclaimer text — single source of truth, so the dashboard,
# README, and any future RAG system prompt all quote the same wording
# rather than drifting into slightly different phrasings over time.
# ---------------------------------------------------------------------------

GOVERNANCE_NOTICE = (
    "HELIX explains and classifies published, de-identified genetic "
    "research data. It does not diagnose, manage, or advise on any "
    "individual's care, and does not accept or process personal genomic "
    "data. All classifications are drawn from public reference sources "
    "(ClinVar, gnomAD, OMIM) or clearly-labeled placeholder/demo logic."
)


def enforce_on_routed_result(summary_label: str, rationale: list[str]) -> BoundaryCheckResult:
    """
    Convenience wrapper for checking a category_router.RoutedCaseResult's
    summary_label and full rationale trail in one call — this is the
    integration point the dashboard should call before rendering any
    routed classification result to a user.
    """
    combined_text = summary_label + " " + " ".join(rationale)
    return check_text_for_boundary_violations(combined_text)