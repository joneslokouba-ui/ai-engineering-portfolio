"""
Module 11 — HELIX: Mitochondrial Sub-Model
=============================================
Per ADR 011: "Heteroplasmy-aware mtDNA scoring." The fifth and final
distinct modeling approach in HELIX. Mitochondrial disorders are
maternally inherited and complicated by heteroplasmy — a cell's
mitochondria are not genetically uniform, and the proportion of
mutant-to-wildtype mtDNA copies (heteroplasmy percentage) varies by
tissue and individual. Most mitochondrial disorders exhibit a
"threshold effect": phenotype is typically silent below a
disorder-specific heteroplasmy threshold and becomes clinically apparent
above it, often with a "variable expression" buffer zone rather than a
sharp cutoff.

Design choice (consistent with Chromosomal's philosophy): rather than
attempt to score arbitrary, unrecognized mtDNA variants via a general
ensemble, this module matches against a CURATED set of well-characterized
pathogenic mtDNA variants (with literature-derived phenotypic
thresholds) and returns "unrecognized — no call" for anything outside
that set. Guessing at heteroplasmy-threshold behavior for a variant with
no established threshold data would be fabricating a number, not
providing a genuine classification — the governance boundary here means
declining to score rather than inventing a threshold.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class KnownMitochondrialVariant:
    variant_id: str            # e.g. "m.3243A>G"
    gene: str                  # e.g. "MT-TL1"
    disorder: str
    # Below (threshold - buffer): typically unaffected.
    # Between (threshold - buffer) and threshold: variable/subclinical expression.
    # At or above threshold: typically affected.
    phenotypic_threshold_pct: float
    threshold_buffer_pct: float


# Curated panel — literature-representative values for portfolio purposes.
# Real thresholds vary by tissue and study; these are illustrative anchors
# for the two curated mitochondrial disorders in the gene panel (ADR 011).
KNOWN_VARIANTS: dict[str, KnownMitochondrialVariant] = {
    "m.3243A>G": KnownMitochondrialVariant(
        variant_id="m.3243A>G",
        gene="MT-TL1",
        disorder="MELAS",
        phenotypic_threshold_pct=60.0,
        threshold_buffer_pct=15.0,   # variable expression zone: 45-60%
    ),
    "m.11778G>A": KnownMitochondrialVariant(
        variant_id="m.11778G>A",
        gene="MT-ND4",
        disorder="Leber Hereditary Optic Neuropathy",
        phenotypic_threshold_pct=70.0,
        threshold_buffer_pct=10.0,   # variable expression zone: 60-70%
    ),
}


class ExpressionTier(str, Enum):
    UNAFFECTED = "Unaffected (below threshold)"
    VARIABLE_EXPRESSION = "Variable expression (within threshold buffer zone)"
    AFFECTED = "Affected (at or above threshold)"


@dataclass
class MitochondrialResult:
    variant_id: str
    matched: bool
    gene: str | None
    disorder: str | None
    heteroplasmy_pct: float
    expression_tier: ExpressionTier | None
    rationale: list[str]


def classify_mitochondrial_variant(
    variant_id: str, heteroplasmy_pct: float
) -> MitochondrialResult:
    """
    Classifies an mtDNA variant against the curated known-pathogenic-variant
    panel, applying heteroplasmy-threshold logic to determine expected
    expression tier.

    Raises ValueError if heteroplasmy_pct is outside [0, 100] — an invalid
    percentage should fail loudly, not be silently clamped.
    """
    if not 0.0 <= heteroplasmy_pct <= 100.0:
        raise ValueError(
            f"heteroplasmy_pct must be in [0.0, 100.0], got {heteroplasmy_pct}"
        )

    rationale: list[str] = [
        f"Variant '{variant_id}' at {heteroplasmy_pct:.1f}% heteroplasmy."
    ]

    known = KNOWN_VARIANTS.get(variant_id)
    if known is None:
        rationale.append(
            "Variant not found in curated known-pathogenic-variant panel — "
            "no established heteroplasmy threshold available. Returning "
            "no call rather than fabricating a threshold for an "
            "uncharacterized variant."
        )
        return MitochondrialResult(
            variant_id=variant_id,
            matched=False,
            gene=None,
            disorder=None,
            heteroplasmy_pct=heteroplasmy_pct,
            expression_tier=None,
            rationale=rationale,
        )

    rationale.append(
        f"Matched to {known.disorder} ({known.gene}). Phenotypic threshold: "
        f"{known.phenotypic_threshold_pct:.1f}%, variable-expression buffer: "
        f"{known.threshold_buffer_pct:.1f} percentage points below threshold."
    )

    lower_buffer_bound = known.phenotypic_threshold_pct - known.threshold_buffer_pct

    if heteroplasmy_pct >= known.phenotypic_threshold_pct:
        tier = ExpressionTier.AFFECTED
        rationale.append(
            f"{heteroplasmy_pct:.1f}% is at or above the "
            f"{known.phenotypic_threshold_pct:.1f}% threshold — clinical "
            f"expression typically expected."
        )
    elif heteroplasmy_pct >= lower_buffer_bound:
        tier = ExpressionTier.VARIABLE_EXPRESSION
        rationale.append(
            f"{heteroplasmy_pct:.1f}% falls within the variable-expression "
            f"buffer zone ({lower_buffer_bound:.1f}%-"
            f"{known.phenotypic_threshold_pct:.1f}%) — expression is "
            f"possible but not guaranteed, and may vary by tissue."
        )
    else:
        tier = ExpressionTier.UNAFFECTED
        rationale.append(
            f"{heteroplasmy_pct:.1f}% is below the "
            f"{lower_buffer_bound:.1f}% buffer floor — clinical expression "
            f"not typically expected at this heteroplasmy level."
        )

    rationale.append(
        "Heteroplasmy level can vary meaningfully by tissue sampled — this "
        "result reflects only the sampled measurement provided, not a "
        "whole-body heteroplasmy state."
    )

    return MitochondrialResult(
        variant_id=variant_id,
        matched=True,
        gene=known.gene,
        disorder=known.disorder,
        heteroplasmy_pct=heteroplasmy_pct,
        expression_tier=tier,
        rationale=rationale,
    )