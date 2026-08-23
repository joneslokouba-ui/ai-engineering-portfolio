"""
Module 11 — HELIX: Multifactorial Sub-Model
==============================================
Per ADR 011: "Simplified polygenic risk score (PRS) over curated
risk-allele set." Multifactorial disorders (e.g. Type 2 Diabetes,
Coronary Heart Disease) have no single causal variant — risk arises from
many small-effect alleles plus environmental/lifestyle contribution. This
is the third distinct modeling approach in HELIX (after variant-ensemble
scoring for Monogenic/X-linked, and karyotype lookup for Chromosomal),
consistent with ADR 011's position that the biology doesn't reduce to one
uniform classifier.

Method (simplified, standard PRS construction):
    PRS = sum(beta_i * dosage_i)   for each risk allele i, dosage in {0,1,2}

The raw score is population-normalized to a z-score using the expected
mean and variance under Hardy-Weinberg equilibrium given each allele's
population frequency, then converted to a percentile. This mirrors how
real PRS tools (e.g. PRSice, LDpred) report results — as a RELATIVE
population percentile, never as an individual risk probability or a
diagnosis. That framing is the governance boundary for this sub-model
specifically: multifactorial disorders are precisely the category where
overclaiming individual predictive power is most tempting and most
misleading, since environment and lifestyle contribute as much or more
than genetics for conditions like Type 2 Diabetes and CHD.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum


@dataclass(frozen=True)
class RiskAllele:
    """A single risk allele in the curated PRS panel for one disorder."""
    rsid: str
    effect_weight: float           # beta / log-odds-ratio-like weight, > 0 increases risk
    population_allele_frequency: float   # 0.0 - 1.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.population_allele_frequency <= 1.0:
            raise ValueError(
                f"population_allele_frequency must be in [0.0, 1.0], "
                f"got {self.population_allele_frequency}"
            )


@dataclass
class AlleleDosage:
    """How many copies (0, 1, or 2) of the risk allele this profile carries."""
    allele: RiskAllele
    dosage: int

    def __post_init__(self) -> None:
        if self.dosage not in (0, 1, 2):
            raise ValueError(f"dosage must be 0, 1, or 2, got {self.dosage}")


class EnvironmentalFactor(str, Enum):
    SMOKING = "smoking"
    OBESITY = "obesity"
    SEDENTARY_LIFESTYLE = "sedentary_lifestyle"
    FAMILY_HISTORY = "family_history"


class RiskTier(str, Enum):
    BELOW_AVERAGE = "Below Average"
    AVERAGE = "Average"
    ABOVE_AVERAGE = "Above Average"
    HIGH = "High"


# Percentile cutpoints — standard PRS reporting convention
_BELOW_AVERAGE_CUTOFF = 25.0
_ABOVE_AVERAGE_CUTOFF = 75.0
_HIGH_CUTOFF = 95.0

# Two or more concurrent environmental risk factors escalate the tier by
# one step — reflects that environment and genetics compound rather than
# act independently, without pretending to quantify that interaction precisely.
_ESCALATION_FACTOR_COUNT = 2

_TIER_ORDER = [RiskTier.BELOW_AVERAGE, RiskTier.AVERAGE, RiskTier.ABOVE_AVERAGE, RiskTier.HIGH]


@dataclass
class PolygenicProfile:
    disorder: str
    dosages: list[AlleleDosage] = field(default_factory=list)
    environmental_factors: list[EnvironmentalFactor] = field(default_factory=list)


@dataclass
class MultifactorialResult:
    disorder: str
    raw_prs_score: float
    z_score: float
    percentile: float
    genetic_tier: RiskTier          # tier from genetics alone, before environmental escalation
    final_tier: RiskTier            # after environmental escalation, if any
    escalated: bool
    rationale: list[str]


def _normal_cdf(z: float) -> float:
    """Standard normal CDF via the error function — no scipy dependency needed."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2)))


def _percentile_to_tier(percentile: float) -> RiskTier:
    if percentile < _BELOW_AVERAGE_CUTOFF:
        return RiskTier.BELOW_AVERAGE
    if percentile < _ABOVE_AVERAGE_CUTOFF:
        return RiskTier.AVERAGE
    if percentile < _HIGH_CUTOFF:
        return RiskTier.ABOVE_AVERAGE
    return RiskTier.HIGH


def _escalate_tier(tier: RiskTier) -> RiskTier:
    idx = _TIER_ORDER.index(tier)
    return _TIER_ORDER[min(idx + 1, len(_TIER_ORDER) - 1)]


def calculate_polygenic_risk(profile: PolygenicProfile) -> MultifactorialResult:
    """
    Computes a population-normalized polygenic risk percentile and maps it
    to a relative risk tier, with an environmental escalation layer on top.

    Raises ValueError if the profile has no risk alleles — a PRS with zero
    inputs is not a valid (even if low) risk estimate, it's a missing
    computation, and callers should not receive a silently misleading
    "Below Average" result for an empty profile.
    """
    if not profile.dosages:
        raise ValueError(
            "PolygenicProfile.dosages is empty — cannot compute a PRS "
            "with zero risk alleles. This indicates missing panel data, "
            "not a genuinely low-risk result."
        )

    rationale: list[str] = [
        f"Computing PRS for '{profile.disorder}' over "
        f"{len(profile.dosages)} curated risk alleles."
    ]

    raw_score = sum(d.allele.effect_weight * d.dosage for d in profile.dosages)

    # Expected mean/variance under Hardy-Weinberg equilibrium, given each
    # allele's population frequency — standard PRS normalization approach.
    expected_mean = sum(
        d.allele.effect_weight * 2 * d.allele.population_allele_frequency
        for d in profile.dosages
    )
    expected_variance = sum(
        (d.allele.effect_weight ** 2) * 2 * d.allele.population_allele_frequency
        * (1 - d.allele.population_allele_frequency)
        for d in profile.dosages
    )

    rationale.append(
        f"Raw PRS = {raw_score:.4f}; population-expected mean = "
        f"{expected_mean:.4f}, variance = {expected_variance:.6f}."
    )

    if expected_variance <= 0:
        # Degenerate case: every allele frequency is 0 or 1 (no population
        # variation) — cannot compute a meaningful z-score.
        rationale.append(
            "Population variance is zero (all allele frequencies at 0 or "
            "1, i.e. no population variation) — z-score undefined. "
            "Returning Average tier as a neutral default rather than "
            "dividing by zero."
        )
        return MultifactorialResult(
            disorder=profile.disorder,
            raw_prs_score=round(raw_score, 4),
            z_score=0.0,
            percentile=50.0,
            genetic_tier=RiskTier.AVERAGE,
            final_tier=RiskTier.AVERAGE,
            escalated=False,
            rationale=rationale,
        )

    z_score = (raw_score - expected_mean) / math.sqrt(expected_variance)
    percentile = _normal_cdf(z_score) * 100.0

    rationale.append(f"z-score = {z_score:.4f}, population percentile = {percentile:.1f}.")

    genetic_tier = _percentile_to_tier(percentile)
    rationale.append(f"Genetic-only tier: {genetic_tier.value}.")

    final_tier = genetic_tier
    escalated = False
    if len(profile.environmental_factors) >= _ESCALATION_FACTOR_COUNT:
        final_tier = _escalate_tier(genetic_tier)
        escalated = final_tier != genetic_tier
        factor_names = ", ".join(f.value for f in profile.environmental_factors)
        rationale.append(
            f"{len(profile.environmental_factors)} concurrent environmental "
            f"factors present ({factor_names}) — tier escalated from "
            f"{genetic_tier.value} to {final_tier.value}. This is a "
            f"qualitative escalation, not a precisely quantified "
            f"gene-environment interaction."
        )
    else:
        rationale.append(
            "Fewer than 2 concurrent environmental factors — no escalation applied."
        )

    rationale.append(
        "This is a RELATIVE population risk percentile, not an individual "
        "diagnosis or a prediction of disease onset — per ADR 011 "
        "governance boundary."
    )

    return MultifactorialResult(
        disorder=profile.disorder,
        raw_prs_score=round(raw_score, 4),
        z_score=round(z_score, 4),
        percentile=round(percentile, 2),
        genetic_tier=genetic_tier,
        final_tier=final_tier,
        escalated=escalated,
        rationale=rationale,
    )