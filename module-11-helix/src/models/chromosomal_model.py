"""
Module 11 — HELIX: Chromosomal Sub-Model
===========================================
Per ADR 011: "Karyotype-pattern lookup" — deliberately NOT a variant-level
scoring ensemble like Monogenic/X-linked. Chromosomal disorders (e.g. Down
Syndrome, Turner Syndrome) arise from numerical or structural chromosome
abnormalities, not single-nucleotide variants — there is no consequence
type, no conservation score, no gnomAD allele frequency to reason about.
Forcing this into the Monogenic scoring shape would misrepresent the
underlying biology (this was the exact reasoning that led ADR 011 to
reject a single unified model across all five categories).

Input here is a karyotype string in simplified ISCN-style notation
(e.g. "47,XX,+21" for full trisomy 21, or a mosaic form like
"47,XX,+21[80]/46,XX[20]" meaning 80% of cells trisomic, 20% normal).
This module does not attempt full ISCN grammar support — only the
patterns relevant to the curated gene/disorder panel (see ADR 011,
data/processed/curated_gene_panel.csv). Anything outside that pattern set
returns "no match" rather than guessing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class KaryotypePattern(str, Enum):
    TRISOMY_21 = "trisomy_21"          # Down Syndrome
    MONOSOMY_X = "monosomy_x"          # Turner Syndrome (45,X)
    KLINEFELTER = "klinefelter"        # 47,XXY
    NORMAL_46XX = "normal_46xx"
    NORMAL_46XY = "normal_46xy"


@dataclass
class KaryotypeEntry:
    disorder: str
    phenotype_summary: str


KARYOTYPE_LOOKUP: dict[KaryotypePattern, KaryotypeEntry] = {
    KaryotypePattern.TRISOMY_21: KaryotypeEntry(
        disorder="Down Syndrome",
        phenotype_summary=(
            "Characteristic facial features, developmental delay, "
            "increased risk of congenital heart defects."
        ),
    ),
    KaryotypePattern.MONOSOMY_X: KaryotypeEntry(
        disorder="Turner Syndrome",
        phenotype_summary=(
            "Short stature, ovarian insufficiency, increased risk of "
            "cardiac and renal anomalies."
        ),
    ),
    KaryotypePattern.KLINEFELTER: KaryotypeEntry(
        disorder="Klinefelter Syndrome",
        phenotype_summary=(
            "Tall stature, hypogonadism, variable learning differences — "
            "included here as a secondary reference case beyond the "
            "primary curated panel."
        ),
    ),
    KaryotypePattern.NORMAL_46XX: KaryotypeEntry(
        disorder="No chromosomal abnormality detected",
        phenotype_summary="Normal female karyotype.",
    ),
    KaryotypePattern.NORMAL_46XY: KaryotypeEntry(
        disorder="No chromosomal abnormality detected",
        phenotype_summary="Normal male karyotype.",
    ),
}

# Simplified ISCN-style pattern matchers. Order matters: mosaic forms
# ("A[xx]/B[yy]") are checked before plain forms since a mosaic string
# would otherwise partially match a plain-form regex.
_PLAIN_PATTERNS: list[tuple[re.Pattern, KaryotypePattern]] = [
    (re.compile(r"^47,X[XY],\+21$"), KaryotypePattern.TRISOMY_21),
    (re.compile(r"^45,X$"), KaryotypePattern.MONOSOMY_X),
    (re.compile(r"^47,XXY$"), KaryotypePattern.KLINEFELTER),
    (re.compile(r"^46,XX$"), KaryotypePattern.NORMAL_46XX),
    (re.compile(r"^46,XY$"), KaryotypePattern.NORMAL_46XY),
]

_MOSAIC_PATTERN = re.compile(
    r"^(?P<abnormal>[^\[]+)\[(?P<abnormal_pct>\d{1,3})\]/"
    r"(?P<normal>[^\[]+)\[(?P<normal_pct>\d{1,3})\]$"
)


class MatchConfidence(str, Enum):
    FULL = "full"          # 100% of cells carry the abnormality
    MOSAIC_HIGH = "mosaic_high"    # >=50% abnormal cells
    MOSAIC_LOW = "mosaic_low"      # <50% abnormal cells
    NONE = "none"


@dataclass
class ChromosomalResult:
    pattern: KaryotypePattern | None
    disorder: str
    phenotype_summary: str
    confidence: MatchConfidence
    mosaic_percentage: float | None    # None if not mosaic
    rationale: list[str]


def _match_plain(karyotype: str) -> KaryotypePattern | None:
    for regex, pattern in _PLAIN_PATTERNS:
        if regex.match(karyotype):
            return pattern
    return None


def classify_karyotype(karyotype: str) -> ChromosomalResult:
    """
    Looks up a karyotype string against the curated pattern set.

    Handles both plain karyotypes ("47,XX,+21") and simplified mosaic
    notation ("47,XX,+21[80]/46,XX[20]"). Anything outside the curated
    pattern set returns pattern=None with confidence=NONE rather than a
    best-effort guess — an unrecognized karyotype must not be silently
    misclassified.
    """
    karyotype = karyotype.strip()
    rationale: list[str] = [f"Input karyotype: '{karyotype}'"]

    mosaic_match = _MOSAIC_PATTERN.match(karyotype)
    if mosaic_match:
        abnormal_str = mosaic_match.group("abnormal").strip()
        abnormal_pct = int(mosaic_match.group("abnormal_pct"))
        normal_pct = int(mosaic_match.group("normal_pct"))

        rationale.append(
            f"Detected mosaic notation: {abnormal_pct}% abnormal cell line "
            f"('{abnormal_str}'), {normal_pct}% normal cell line."
        )

        pattern = _match_plain(abnormal_str)
        if pattern is None:
            rationale.append(
                f"Abnormal cell line '{abnormal_str}' does not match any "
                f"curated pattern — returning no match."
            )
            return ChromosomalResult(
                pattern=None,
                disorder="Unrecognized karyotype",
                phenotype_summary="",
                confidence=MatchConfidence.NONE,
                mosaic_percentage=abnormal_pct,
                rationale=rationale,
            )

        entry = KARYOTYPE_LOOKUP[pattern]
        confidence = (
            MatchConfidence.MOSAIC_HIGH if abnormal_pct >= 50
            else MatchConfidence.MOSAIC_LOW
        )
        rationale.append(
            f"Matched '{abnormal_str}' to {entry.disorder}. Mosaic "
            f"confidence: {confidence.value} ({abnormal_pct}% abnormal "
            f"cell line) — phenotype expression in mosaic cases is "
            f"typically milder and more variable than full trisomy/"
            f"monosomy, proportional to abnormal cell-line percentage."
        )
        return ChromosomalResult(
            pattern=pattern,
            disorder=entry.disorder,
            phenotype_summary=entry.phenotype_summary,
            confidence=confidence,
            mosaic_percentage=float(abnormal_pct),
            rationale=rationale,
        )

    # Plain (non-mosaic) karyotype
    pattern = _match_plain(karyotype)
    if pattern is None:
        rationale.append("No match found in curated karyotype pattern set.")
        return ChromosomalResult(
            pattern=None,
            disorder="Unrecognized karyotype",
            phenotype_summary="",
            confidence=MatchConfidence.NONE,
            mosaic_percentage=None,
            rationale=rationale,
        )

    entry = KARYOTYPE_LOOKUP[pattern]
    rationale.append(f"Matched to {entry.disorder} (full, non-mosaic).")
    return ChromosomalResult(
        pattern=pattern,
        disorder=entry.disorder,
        phenotype_summary=entry.phenotype_summary,
        confidence=MatchConfidence.FULL,
        mosaic_percentage=None,
        rationale=rationale,
    )