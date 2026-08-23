"""
Module 11 — HELIX: Monogenic sub-model regression tests

Run: pytest test_monogenic_model.py -v
"""

import pytest

from src.models.monogenic_model import (
    ClassificationResult,
    ConsequenceType,
    ReviewStatus,
    Tier,
    VariantFeatures,
    classify_monogenic_variant,
)


class TestVariantFeaturesValidation:
    def test_rejects_out_of_range_conservation_score(self):
        with pytest.raises(ValueError):
            VariantFeatures(
                gene="CFTR",
                consequence=ConsequenceType.MISSENSE,
                review_status=ReviewStatus.EXPERT_PANEL,
                conservation_score=1.5,
                gnomad_allele_frequency=0.001,
            )

    def test_rejects_out_of_range_allele_frequency(self):
        with pytest.raises(ValueError):
            VariantFeatures(
                gene="CFTR",
                consequence=ConsequenceType.MISSENSE,
                review_status=ReviewStatus.EXPERT_PANEL,
                conservation_score=0.5,
                gnomad_allele_frequency=1.5,
            )

    def test_accepts_boundary_values(self):
        # 0.0 and 1.0 are valid boundaries, should not raise
        VariantFeatures(
            gene="HTT",
            consequence=ConsequenceType.FRAMESHIFT,
            review_status=ReviewStatus.PRACTICE_GUIDELINE,
            conservation_score=1.0,
            gnomad_allele_frequency=0.0,
        )


class TestClearPathogenicCase:
    """
    Frameshift + high conservation + rare + strong review status should
    unambiguously classify as Pathogenic. This is the reference "obvious"
    case the other four sub-models' tests should mirror the shape of.
    """

    def test_frameshift_rare_conserved_expert_reviewed_is_pathogenic(self):
        features = VariantFeatures(
            gene="HTT",
            consequence=ConsequenceType.FRAMESHIFT,
            review_status=ReviewStatus.EXPERT_PANEL,
            conservation_score=0.95,
            gnomad_allele_frequency=0.00001,
        )
        result = classify_monogenic_variant(features)
        assert result.tier == Tier.PATHOGENIC
        assert result.raw_score >= 0.70
        assert result.confidence == pytest.approx(0.9)
        assert len(result.rationale) >= 3


class TestClearBenignCase:
    """
    Synonymous + low conservation + common in population should
    unambiguously classify as Benign, regardless of review status.
    """

    def test_synonymous_common_unconserved_is_benign(self):
        features = VariantFeatures(
            gene="CFTR",
            consequence=ConsequenceType.SYNONYMOUS,
            review_status=ReviewStatus.MULTIPLE_SUBMITTERS,
            conservation_score=0.05,
            gnomad_allele_frequency=0.05,   # well above common threshold
        )
        result = classify_monogenic_variant(features)
        assert result.tier == Tier.BENIGN
        assert result.raw_score <= 0.30


class TestVUSBoundaryBehavior:
    def test_missense_intermediate_signals_is_vus(self):
        features = VariantFeatures(
            gene="HBB",
            consequence=ConsequenceType.MISSENSE,
            review_status=ReviewStatus.MULTIPLE_SUBMITTERS,
            conservation_score=0.5,
            gnomad_allele_frequency=0.002,   # intermediate — no strong adjustment
        )
        result = classify_monogenic_variant(features)
        assert result.tier == Tier.VUS
        assert BENIGN_CUTOFF_EXCLUSIVE(result.raw_score)

    def test_score_of_exactly_pathogenic_cutoff_is_pathogenic_not_vus(self):
        # Boundary check: raw_score == PATHOGENIC_CUTOFF must classify as
        # Pathogenic (>=), not fall into VUS. Constructed via high-severity
        # inputs landing near the 0.70 cutoff with strong review support.
        features = VariantFeatures(
            gene="DMD",
            consequence=ConsequenceType.SPLICE_SITE,   # severity 0.80
            review_status=ReviewStatus.PRACTICE_GUIDELINE,
            conservation_score=0.60,
            gnomad_allele_frequency=0.005,   # intermediate, no adjustment
        )
        result = classify_monogenic_variant(features)
        # base_score = 0.5*0.80 + 0.5*0.60 = 0.70, af_adjustment = 0.0
        assert result.raw_score == pytest.approx(0.70)
        assert result.tier == Tier.PATHOGENIC


def BENIGN_CUTOFF_EXCLUSIVE(score: float) -> bool:
    """Helper: True if score sits strictly inside the VUS band."""
    from src.models.monogenic_model import BENIGN_CUTOFF, PATHOGENIC_CUTOFF
    return BENIGN_CUTOFF < score < PATHOGENIC_CUTOFF


class TestAlleleFrequencyOverride:
    """
    This is the case most likely to catch a real bug: a molecularly severe
    variant (frameshift, highly conserved) that is nonetheless COMMON in
    the population should be pulled down from Pathogenic — a genuinely
    damaging-looking variant that's common is far more likely a benign
    population polymorphism or an annotation error than a real pathogenic
    finding (ACMG BS1 logic).
    """

    def test_severe_consequence_but_common_af_is_not_pathogenic(self):
        features = VariantFeatures(
            gene="CFTR",
            consequence=ConsequenceType.FRAMESHIFT,
            review_status=ReviewStatus.EXPERT_PANEL,
            conservation_score=0.9,
            gnomad_allele_frequency=0.02,   # 2% — well above common threshold
        )
        result = classify_monogenic_variant(features)
        # base_score = 0.5*0.95 + 0.5*0.9 = 0.925, minus 0.35 AF penalty = 0.575
        assert result.tier == Tier.VUS
        assert result.raw_score < PATHOGENIC_CUTOFF_VALUE()


def PATHOGENIC_CUTOFF_VALUE() -> float:
    from src.models.monogenic_model import PATHOGENIC_CUTOFF
    return PATHOGENIC_CUTOFF


class TestReviewStatusConfidenceDowngrade:
    """
    A borderline-pathogenic score backed by weak curatorial evidence
    (no assertion criteria) should be downgraded to VUS rather than
    reported as a confident Pathogenic call — this is the rule most
    important to regression-test since it's easy to accidentally break
    when tuning score thresholds later.
    """

    def test_pathogenic_leaning_score_with_no_assertion_status_downgrades_to_vus(self):
        features = VariantFeatures(
            gene="MLH1",
            consequence=ConsequenceType.NONSENSE,
            review_status=ReviewStatus.NO_ASSERTION,   # weight 0.2, < 0.4 threshold
            conservation_score=0.85,
            gnomad_allele_frequency=0.00005,
        )
        result = classify_monogenic_variant(features)
        assert result.raw_score >= PATHOGENIC_CUTOFF_VALUE(), (
            "test setup invariant: raw score must be in pathogenic range "
            "for the downgrade rule to be meaningfully exercised"
        )
        assert result.tier == Tier.VUS
        assert any("downgraded to VUS" in line for line in result.rationale)

    def test_same_score_with_strong_review_status_stays_pathogenic(self):
        # Identical features except review status — isolates the downgrade
        # rule as the only variable under test.
        features = VariantFeatures(
            gene="MLH1",
            consequence=ConsequenceType.NONSENSE,
            review_status=ReviewStatus.PRACTICE_GUIDELINE,   # weight 1.0
            conservation_score=0.85,
            gnomad_allele_frequency=0.00005,
        )
        result = classify_monogenic_variant(features)
        assert result.tier == Tier.PATHOGENIC


class TestRationaleExplainability:
    """
    Governance boundary (ADR 011) requires classifications to be
    explainable, not opaque — every result must carry a non-trivial
    rationale trail.
    """

    def test_rationale_is_never_empty(self):
        features = VariantFeatures(
            gene="F8",
            consequence=ConsequenceType.MISSENSE,
            review_status=ReviewStatus.SINGLE_SUBMITTER,
            conservation_score=0.4,
            gnomad_allele_frequency=0.0003,
        )
        result = classify_monogenic_variant(features)
        assert isinstance(result, ClassificationResult)
        assert len(result.rationale) >= 3
        assert all(isinstance(line, str) and line for line in result.rationale)


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))