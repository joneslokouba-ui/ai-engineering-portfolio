"""
Module 11 — HELIX: Monogenic Sub-Model
=========================================
Reference implementation for the five category sub-models (ADR 011).
Classifies single-gene variants into Benign / VUS / Pathogenic tiers using
an ensemble of three signals, loosely inspired by ACMG variant
classification guidelines (simplified for portfolio scope — this is NOT a
clinical-grade ACMG implementation):

1. ClinVar review status  — how much curatorial confidence backs the
   existing assertion (0-4 "star" system, mirroring ClinVar's own scale).
2. Variant consequence type — molecular severity (synonymous < missense <
   nonsense/frameshift/splice-site).
3. Conservation score — evolutionary constraint at the variant position
   (0.0 = unconstrained, 1.0 = highly conserved).

A fourth signal, population allele frequency (gnomAD), acts as a
pathogenicity dampener: a variant common in the general population is
unlikely to cause a severe monogenic disorder (ACMG BS1-inspired rule).

This module operates on already-extracted VariantFeatures — it does NOT
parse ClinVar/gnomAD files directly. That is ingestion/clinvar_loader.py's
and ingestion/gnomad_loader.py's job (not yet implemented). Decoupling
scoring logic from ingestion means this model can be built and fully
tested against synthetic feature sets before real data pulls exist —
same incremental-verification approach used throughout the portfolio.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ReviewStatus(str, Enum):
    """Mirrors ClinVar's own review-status star system."""
    PRACTICE_GUIDELINE = "practice guideline"                          # 4 stars
    EXPERT_PANEL = "reviewed by expert panel"                          # 3 stars
    MULTIPLE_SUBMITTERS = "criteria provided, multiple submitters"     # 2 stars
    SINGLE_SUBMITTER = "criteria provided, single submitter"           # 1 star
    NO_ASSERTION = "no assertion criteria provided"                    # 0 stars


REVIEW_STATUS_WEIGHT: dict[ReviewStatus, float] = {
    ReviewStatus.PRACTICE_GUIDELINE: 1.0,
    ReviewStatus.EXPERT_PANEL: 0.9,
    ReviewStatus.MULTIPLE_SUBMITTERS: 0.7,
    ReviewStatus.SINGLE_SUBMITTER: 0.5,
    ReviewStatus.NO_ASSERTION: 0.2,
}


class ConsequenceType(str, Enum):
    SYNONYMOUS = "synonymous"
    MISSENSE = "missense"
    IN_FRAME_INDEL = "in_frame_indel"   # e.g. CFTR p.Phe508del — deletion/insertion
                                          # in multiples of 3 nt, preserves reading
                                          # frame but can still be highly disruptive
    SPLICE_SITE = "splice_site"
    NONSENSE = "nonsense"
    FRAMESHIFT = "frameshift"


CONSEQUENCE_SEVERITY: dict[ConsequenceType, float] = {
    ConsequenceType.SYNONYMOUS: 0.05,
    ConsequenceType.MISSENSE: 0.55,
    ConsequenceType.IN_FRAME_INDEL: 0.75,   # below nonsense/frameshift (no premature
                                              # truncation) but above ordinary missense —
                                              # loss of one or more residues can still
                                              # substantially disrupt protein folding
                                              # (ΔF508 in CFTR being the canonical example)
    ConsequenceType.SPLICE_SITE: 0.80,
    ConsequenceType.NONSENSE: 0.90,
    ConsequenceType.FRAMESHIFT: 0.95,
}

# ACMG BS1-inspired: population frequency above this threshold is treated
# as strong evidence against pathogenicity for a typical monogenic disorder.
COMMON_VARIANT_AF_THRESHOLD = 0.01     # 1% gnomAD allele frequency
RARE_VARIANT_AF_THRESHOLD = 0.0001     # 0.01% — rarity supports pathogenicity

PATHOGENIC_CUTOFF = 0.70
BENIGN_CUTOFF = 0.30


class Tier(str, Enum):
    BENIGN = "Benign"
    VUS = "VUS"
    PATHOGENIC = "Pathogenic"


@dataclass
class VariantFeatures:
    """Already-extracted, per-variant inputs — output of the ingestion layer."""
    gene: str
    consequence: ConsequenceType
    review_status: ReviewStatus
    conservation_score: float          # 0.0 - 1.0
    gnomad_allele_frequency: float     # 0.0 - 1.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.conservation_score <= 1.0:
            raise ValueError(
                f"conservation_score must be in [0.0, 1.0], got {self.conservation_score}"
            )
        if not 0.0 <= self.gnomad_allele_frequency <= 1.0:
            raise ValueError(
                f"gnomad_allele_frequency must be in [0.0, 1.0], "
                f"got {self.gnomad_allele_frequency}"
            )


@dataclass
class ClassificationResult:
    tier: Tier
    raw_score: float                   # 0.0 (benign-leaning) - 1.0 (pathogenic-leaning)
    confidence: float                  # driven by review status weight
    rationale: list[str]


def _frequency_adjustment(af: float) -> tuple[float, str]:
    """
    Returns a signed adjustment to the pathogenicity score based on
    population allele frequency, plus a human-readable rationale line.
    """
    if af >= COMMON_VARIANT_AF_THRESHOLD:
        return -0.35, (
            f"Allele frequency {af:.4f} exceeds common-variant threshold "
            f"({COMMON_VARIANT_AF_THRESHOLD}) — strong evidence against "
            f"pathogenicity for a monogenic disorder (BS1-inspired)."
        )
    if af <= RARE_VARIANT_AF_THRESHOLD:
        return 0.10, (
            f"Allele frequency {af:.6f} is below the rare-variant threshold "
            f"({RARE_VARIANT_AF_THRESHOLD}) — consistent with, but not "
            f"proof of, pathogenicity."
        )
    return 0.0, f"Allele frequency {af:.4f} is intermediate — no strong adjustment."


def classify_monogenic_variant(features: VariantFeatures) -> ClassificationResult:
    """
    Ensemble classification combining consequence severity, conservation,
    review-status confidence weighting, and a population-frequency
    adjustment, into a Benign / VUS / Pathogenic tier.

    This is a simplified, explainable ensemble for portfolio purposes —
    it is explicitly NOT a clinical-grade ACMG implementation and must
    never be presented as one (see ADR 011 governance boundary).
    """
    rationale: list[str] = []

    consequence_component = CONSEQUENCE_SEVERITY[features.consequence]
    rationale.append(
        f"Consequence '{features.consequence.value}' contributes severity "
        f"{consequence_component:.2f}."
    )

    conservation_component = features.conservation_score
    rationale.append(
        f"Conservation score contributes {conservation_component:.2f}."
    )

    base_score = 0.5 * consequence_component + 0.5 * conservation_component

    af_adjustment, af_rationale = _frequency_adjustment(features.gnomad_allele_frequency)
    rationale.append(af_rationale)

    raw_score = min(1.0, max(0.0, base_score + af_adjustment))

    review_weight = REVIEW_STATUS_WEIGHT[features.review_status]
    rationale.append(
        f"Review status '{features.review_status.value}' yields confidence "
        f"weight {review_weight:.2f}."
    )

    if raw_score >= PATHOGENIC_CUTOFF:
        tier = Tier.PATHOGENIC
    elif raw_score <= BENIGN_CUTOFF:
        tier = Tier.BENIGN
    else:
        tier = Tier.VUS

    # Low review-status confidence pulls a borderline call toward VUS —
    # a weakly-supported "Pathogenic" or "Benign" call is exactly what VUS
    # exists to represent.
    if tier != Tier.VUS and review_weight < 0.4:
        rationale.append(
            f"Review-status confidence ({review_weight:.2f}) too low to "
            f"support a definitive {tier.value} call — downgraded to VUS."
        )
        tier = Tier.VUS

    return ClassificationResult(
        tier=tier,
        raw_score=round(raw_score, 4),
        confidence=review_weight,
        rationale=rationale,
    )