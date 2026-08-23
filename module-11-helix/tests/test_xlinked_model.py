"""
Module 11 — HELIX: X-linked sub-model regression tests

Run: pytest test_xlinked_model.py -v
"""

import pytest

from src.models.monogenic_model import ConsequenceType, ReviewStatus, Tier, VariantFeatures
from src.models.xlinked_model import (
    ExpressionStatus,
    XLinkedFeatures,
    Zygosity,
    classify_xlinked_variant,
)


def _pathogenic_variant() -> VariantFeatures:
    """A variant that reliably classifies as Pathogenic via the shared engine."""
    return VariantFeatures(
        gene="DMD",
        consequence=ConsequenceType.FRAMESHIFT,
        review_status=ReviewStatus.EXPERT_PANEL,
        conservation_score=0.9,
        gnomad_allele_frequency=0.00001,
    )


def _benign_variant() -> VariantFeatures:
    return VariantFeatures(
        gene="F8",
        consequence=ConsequenceType.SYNONYMOUS,
        review_status=ReviewStatus.MULTIPLE_SUBMITTERS,
        conservation_score=0.05,
        gnomad_allele_frequency=0.05,
    )


class TestHemizygousExpression:
    def test_pathogenic_hemizygous_is_affected(self):
        features = XLinkedFeatures(variant=_pathogenic_variant(), zygosity=Zygosity.HEMIZYGOUS)
        result = classify_xlinked_variant(features)
        assert result.tier == Tier.PATHOGENIC
        assert result.expression_status == ExpressionStatus.AFFECTED
        assert any("Hemizygous" in line for line in result.rationale)


class TestHeterozygousExpression:
    def test_pathogenic_heterozygous_is_carrier_with_variable_expression_flag(self):
        features = XLinkedFeatures(variant=_pathogenic_variant(), zygosity=Zygosity.HETEROZYGOUS)
        result = classify_xlinked_variant(features)
        assert result.tier == Tier.PATHOGENIC
        assert result.expression_status == ExpressionStatus.CARRIER_VARIABLE_EXPRESSION
        assert any("X-inactivation" in line for line in result.rationale)

    def test_heterozygous_never_reports_plain_affected(self):
        # Regression guard: heterozygous carriers must never collapse into
        # the same "Affected" bucket as hemizygous/homozygous — that would
        # misrepresent typical X-linked recessive carrier status.
        features = XLinkedFeatures(variant=_pathogenic_variant(), zygosity=Zygosity.HETEROZYGOUS)
        result = classify_xlinked_variant(features)
        assert result.expression_status != ExpressionStatus.AFFECTED


class TestHomozygousExpression:
    def test_pathogenic_homozygous_is_affected(self):
        features = XLinkedFeatures(variant=_pathogenic_variant(), zygosity=Zygosity.HOMOZYGOUS)
        result = classify_xlinked_variant(features)
        assert result.tier == Tier.PATHOGENIC
        assert result.expression_status == ExpressionStatus.AFFECTED


class TestNonPathogenicShortCircuit:
    """
    Expression status should never be called (Affected/Carrier) unless the
    underlying variant classification is confidently Pathogenic — a Benign
    or VUS variant should never generate an expression claim.
    """

    def test_benign_variant_any_zygosity_is_not_applicable(self):
        for zygosity in Zygosity:
            features = XLinkedFeatures(variant=_benign_variant(), zygosity=zygosity)
            result = classify_xlinked_variant(features)
            assert result.tier == Tier.BENIGN
            assert result.expression_status == ExpressionStatus.NOT_APPLICABLE

    def test_vus_variant_is_not_applicable(self):
        vus_variant = VariantFeatures(
            gene="DMD",
            consequence=ConsequenceType.MISSENSE,
            review_status=ReviewStatus.MULTIPLE_SUBMITTERS,
            conservation_score=0.5,
            gnomad_allele_frequency=0.002,
        )
        features = XLinkedFeatures(variant=vus_variant, zygosity=Zygosity.HEMIZYGOUS)
        result = classify_xlinked_variant(features)
        assert result.tier == Tier.VUS
        assert result.expression_status == ExpressionStatus.NOT_APPLICABLE


class TestSharedEngineConsistency:
    """
    The X-linked model must produce IDENTICAL variant-level tier and score
    to the Monogenic model for the same VariantFeatures input — it should
    only add the expression layer, never alter the underlying scoring.
    This is the regression test most likely to catch an accidental
    divergence if someone edits monogenic_model.py later without updating
    this dependent module.
    """

    def test_tier_and_score_match_monogenic_engine_directly(self):
        from src.models.monogenic_model import classify_monogenic_variant

        variant = _pathogenic_variant()
        direct_result = classify_monogenic_variant(variant)

        xlinked_result = classify_xlinked_variant(
            XLinkedFeatures(variant=variant, zygosity=Zygosity.HEMIZYGOUS)
        )

        assert xlinked_result.variant_classification.tier == direct_result.tier
        assert xlinked_result.variant_classification.raw_score == direct_result.raw_score


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))