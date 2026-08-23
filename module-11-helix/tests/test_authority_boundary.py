"""
Module 11 — HELIX: Authority boundary regression tests

Run: pytest test_authority_boundary.py -v
"""

import pytest

from src.governance.authority_boundary import (
    BoundaryViolationSeverity,
    check_text_for_boundary_violations,
    enforce_on_routed_result,
)


class TestBlockingPatterns:
    def test_directive_you_should_see_a_doctor_is_blocked(self):
        result = check_text_for_boundary_violations("You should see a doctor immediately.")
        assert result.passed is False
        assert result.severity == BoundaryViolationSeverity.BLOCKING

    def test_you_have_condition_is_blocked(self):
        result = check_text_for_boundary_violations("Based on this variant, you have Cystic Fibrosis.")
        assert result.passed is False
        assert result.severity == BoundaryViolationSeverity.BLOCKING

    def test_i_diagnose_is_blocked(self):
        result = check_text_for_boundary_violations("I diagnose this as pathogenic disease.")
        assert result.passed is False

    def test_your_diagnosis_is_phrasing_is_blocked(self):
        result = check_text_for_boundary_violations("Your diagnosis is Huntington's Disease.")
        assert result.passed is False


class TestAdvisoryPatterns:
    def test_you_should_consider_is_advisory_not_blocking(self):
        result = check_text_for_boundary_violations("You should consider discussing this with a specialist.")
        assert result.passed is True   # advisory does not fail the check
        assert result.severity == BoundaryViolationSeverity.ADVISORY

    def test_in_your_case_is_advisory(self):
        result = check_text_for_boundary_violations("In your case, the variant is rare.")
        assert result.severity == BoundaryViolationSeverity.ADVISORY


class TestCleanText:
    def test_population_level_language_passes_clean(self):
        result = check_text_for_boundary_violations(
            "This variant is classified as Pathogenic based on ClinVar "
            "expert panel review and high conservation."
        )
        assert result.passed is True
        assert result.severity == BoundaryViolationSeverity.NONE
        assert result.flagged_phrases == []

    def test_empty_string_passes_clean(self):
        result = check_text_for_boundary_violations("")
        assert result.passed is True
        assert result.severity == BoundaryViolationSeverity.NONE


class TestExistingSubModelRationalePassesTheBoundary:
    """
    Critical integration check: every rationale string already produced
    by the five sub-models built earlier in HELIX must pass this
    boundary — if a sub-model's own explanation text accidentally uses
    blocking language, that's a real bug this test would catch.
    """

    def test_monogenic_rationale_passes(self):
        from src.models.monogenic_model import (
            ConsequenceType, ReviewStatus, VariantFeatures, classify_monogenic_variant,
        )
        features = VariantFeatures(
            gene="HTT",
            consequence=ConsequenceType.FRAMESHIFT,
            review_status=ReviewStatus.EXPERT_PANEL,
            conservation_score=0.95,
            gnomad_allele_frequency=0.00001,
        )
        result = classify_monogenic_variant(features)
        boundary_result = enforce_on_routed_result(result.tier.value, result.rationale)
        assert boundary_result.passed is True

    def test_xlinked_rationale_passes(self):
        from src.models.monogenic_model import ConsequenceType, ReviewStatus, VariantFeatures
        from src.models.xlinked_model import XLinkedFeatures, Zygosity, classify_xlinked_variant

        variant = VariantFeatures(
            gene="DMD",
            consequence=ConsequenceType.FRAMESHIFT,
            review_status=ReviewStatus.EXPERT_PANEL,
            conservation_score=0.9,
            gnomad_allele_frequency=0.00001,
        )
        result = classify_xlinked_variant(XLinkedFeatures(variant=variant, zygosity=Zygosity.HETEROZYGOUS))
        boundary_result = enforce_on_routed_result(result.tier.value, result.rationale)
        assert boundary_result.passed is True

    def test_chromosomal_rationale_passes(self):
        from src.models.chromosomal_model import classify_karyotype

        result = classify_karyotype("47,XX,+21[80]/46,XX[20]")
        boundary_result = enforce_on_routed_result(result.disorder, result.rationale)
        assert boundary_result.passed is True

    def test_multifactorial_rationale_passes(self):
        from src.models.multifactorial_model import (
            AlleleDosage, EnvironmentalFactor, PolygenicProfile, RiskAllele,
            calculate_polygenic_risk,
        )

        allele = RiskAllele(rsid="rs1", effect_weight=0.3, population_allele_frequency=0.5)
        profile = PolygenicProfile(
            disorder="Type 2 Diabetes",
            dosages=[AlleleDosage(allele=allele, dosage=1)],
            environmental_factors=[EnvironmentalFactor.OBESITY, EnvironmentalFactor.SMOKING],
        )
        result = calculate_polygenic_risk(profile)
        boundary_result = enforce_on_routed_result(result.final_tier.value, result.rationale)
        assert boundary_result.passed is True

    def test_mitochondrial_rationale_passes(self):
        from src.models.mitochondrial_model import classify_mitochondrial_variant

        result = classify_mitochondrial_variant("m.3243A>G", 70.0)
        boundary_result = enforce_on_routed_result(result.disorder or "", result.rationale)
        assert boundary_result.passed is True


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))