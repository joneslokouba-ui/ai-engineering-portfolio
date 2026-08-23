"""
Module 11 — HELIX: Mitochondrial sub-model regression tests

Run: pytest test_mitochondrial_model.py -v
"""

import pytest

from src.models.mitochondrial_model import (
    ExpressionTier,
    classify_mitochondrial_variant,
)


class TestHeteroplasmyValidation:
    def test_rejects_negative_heteroplasmy(self):
        with pytest.raises(ValueError):
            classify_mitochondrial_variant("m.3243A>G", -1.0)

    def test_rejects_heteroplasmy_above_100(self):
        with pytest.raises(ValueError):
            classify_mitochondrial_variant("m.3243A>G", 100.1)

    def test_accepts_boundary_values(self):
        # Should not raise
        classify_mitochondrial_variant("m.3243A>G", 0.0)
        classify_mitochondrial_variant("m.3243A>G", 100.0)


class TestKnownVariantMatching:
    def test_melas_variant_matches_correct_gene_and_disorder(self):
        result = classify_mitochondrial_variant("m.3243A>G", 70.0)
        assert result.matched is True
        assert result.gene == "MT-TL1"
        assert result.disorder == "MELAS"

    def test_lhon_variant_matches_correct_gene_and_disorder(self):
        result = classify_mitochondrial_variant("m.11778G>A", 80.0)
        assert result.matched is True
        assert result.gene == "MT-ND4"
        assert result.disorder == "Leber Hereditary Optic Neuropathy"


class TestThresholdEffectTiers:
    """
    MELAS variant (m.3243A>G): threshold=60%, buffer=15% -> buffer zone 45-60%.
    """

    def test_low_heteroplasmy_is_unaffected(self):
        result = classify_mitochondrial_variant("m.3243A>G", 20.0)
        assert result.expression_tier == ExpressionTier.UNAFFECTED

    def test_just_below_buffer_floor_is_unaffected(self):
        result = classify_mitochondrial_variant("m.3243A>G", 44.9)
        assert result.expression_tier == ExpressionTier.UNAFFECTED

    def test_at_buffer_floor_is_variable_expression(self):
        # lower_buffer_bound = 60 - 15 = 45.0 exactly, inclusive
        result = classify_mitochondrial_variant("m.3243A>G", 45.0)
        assert result.expression_tier == ExpressionTier.VARIABLE_EXPRESSION

    def test_mid_buffer_zone_is_variable_expression(self):
        result = classify_mitochondrial_variant("m.3243A>G", 52.0)
        assert result.expression_tier == ExpressionTier.VARIABLE_EXPRESSION

    def test_just_below_threshold_is_variable_expression(self):
        result = classify_mitochondrial_variant("m.3243A>G", 59.9)
        assert result.expression_tier == ExpressionTier.VARIABLE_EXPRESSION

    def test_at_threshold_exactly_is_affected(self):
        # Boundary: >= threshold must be Affected, not Variable
        result = classify_mitochondrial_variant("m.3243A>G", 60.0)
        assert result.expression_tier == ExpressionTier.AFFECTED

    def test_high_heteroplasmy_is_affected(self):
        result = classify_mitochondrial_variant("m.3243A>G", 95.0)
        assert result.expression_tier == ExpressionTier.AFFECTED


class TestDifferentThresholdsPerDisorder:
    """
    LHON variant (m.11778G>A): threshold=70%, buffer=10% -> buffer zone 60-70%.
    Confirms thresholds are variant-specific, not a shared global constant.
    """

    def test_lhon_at_melas_threshold_is_still_unaffected(self):
        # 60% would be AFFECTED for MELAS, but LHON's buffer floor is also
        # 60% (70 - 10) so at exactly 60% LHON should be Variable, not Affected.
        result = classify_mitochondrial_variant("m.11778G>A", 60.0)
        assert result.expression_tier == ExpressionTier.VARIABLE_EXPRESSION

    def test_lhon_below_60_is_unaffected(self):
        result = classify_mitochondrial_variant("m.11778G>A", 55.0)
        assert result.expression_tier == ExpressionTier.UNAFFECTED

    def test_lhon_at_threshold_is_affected(self):
        result = classify_mitochondrial_variant("m.11778G>A", 70.0)
        assert result.expression_tier == ExpressionTier.AFFECTED


class TestUnrecognizedVariants:
    """
    A variant with no established threshold must never receive a
    fabricated expression tier — this is the governance boundary for
    this specific sub-model.
    """

    def test_unrecognized_variant_returns_no_match(self):
        result = classify_mitochondrial_variant("m.9999X>Y", 80.0)
        assert result.matched is False
        assert result.gene is None
        assert result.disorder is None
        assert result.expression_tier is None

    def test_unrecognized_variant_rationale_explains_why(self):
        result = classify_mitochondrial_variant("m.9999X>Y", 80.0)
        assert any("no established heteroplasmy threshold" in line for line in result.rationale)

    def test_unrecognized_variant_still_returns_heteroplasmy_value(self):
        # The input value should be echoed back even on no-match, since it
        # was validly parsed even though the variant itself wasn't recognized.
        result = classify_mitochondrial_variant("m.9999X>Y", 42.5)
        assert result.heteroplasmy_pct == 42.5


class TestTissueVariabilityDisclosure:
    def test_matched_result_notes_tissue_sampling_caveat(self):
        result = classify_mitochondrial_variant("m.3243A>G", 70.0)
        assert any("tissue" in line.lower() for line in result.rationale)


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))