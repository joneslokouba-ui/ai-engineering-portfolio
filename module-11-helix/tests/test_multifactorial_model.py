"""
Module 11 — HELIX: Multifactorial sub-model regression tests

Run: pytest test_multifactorial_model.py -v
"""

import pytest

from src.models.multifactorial_model import (
    AlleleDosage,
    EnvironmentalFactor,
    MultifactorialResult,
    PolygenicProfile,
    RiskAllele,
    RiskTier,
    calculate_polygenic_risk,
)


def _make_allele(rsid: str, weight: float, af: float) -> RiskAllele:
    return RiskAllele(rsid=rsid, effect_weight=weight, population_allele_frequency=af)


class TestRiskAlleleValidation:
    def test_rejects_out_of_range_allele_frequency(self):
        with pytest.raises(ValueError):
            RiskAllele(rsid="rs1", effect_weight=0.2, population_allele_frequency=1.5)

    def test_rejects_invalid_dosage(self):
        allele = _make_allele("rs1", 0.2, 0.3)
        with pytest.raises(ValueError):
            AlleleDosage(allele=allele, dosage=3)


class TestEmptyProfileGuard:
    def test_empty_dosages_raises_rather_than_silently_defaulting(self):
        profile = PolygenicProfile(disorder="Type 2 Diabetes", dosages=[])
        with pytest.raises(ValueError):
            calculate_polygenic_risk(profile)


class TestPercentileAndTierMapping:
    def test_average_dosage_profile_lands_near_50th_percentile(self):
        # Each dosage set to the population-expected value (2 * af) rounded
        # to nearest int should land the raw score close to the expected
        # mean, i.e. near the 50th percentile / Average tier.
        alleles = [
            _make_allele("rs1", 0.3, 0.5),   # expected dosage 2*0.5=1.0
            _make_allele("rs2", 0.25, 0.5),
            _make_allele("rs3", 0.4, 0.5),
        ]
        dosages = [AlleleDosage(allele=a, dosage=1) for a in alleles]
        profile = PolygenicProfile(disorder="Type 2 Diabetes", dosages=dosages)
        result = calculate_polygenic_risk(profile)
        assert result.genetic_tier == RiskTier.AVERAGE
        assert 25.0 <= result.percentile < 75.0

    def test_high_dosage_of_high_weight_alleles_yields_high_tier(self):
        alleles = [
            _make_allele("rs1", 0.8, 0.1),
            _make_allele("rs2", 0.9, 0.1),
            _make_allele("rs3", 0.85, 0.1),
        ]
        # dosage=2 (both copies) of rare, high-effect alleles — far above
        # population expectation
        dosages = [AlleleDosage(allele=a, dosage=2) for a in alleles]
        profile = PolygenicProfile(disorder="Coronary Heart Disease", dosages=dosages)
        result = calculate_polygenic_risk(profile)
        assert result.genetic_tier == RiskTier.HIGH
        assert result.percentile >= 95.0

    def test_zero_dosage_of_risk_alleles_yields_below_average_tier(self):
        alleles = [
            _make_allele("rs1", 0.6, 0.3),
            _make_allele("rs2", 0.5, 0.3),
        ]
        dosages = [AlleleDosage(allele=a, dosage=0) for a in alleles]
        profile = PolygenicProfile(disorder="Type 2 Diabetes", dosages=dosages)
        result = calculate_polygenic_risk(profile)
        assert result.genetic_tier == RiskTier.BELOW_AVERAGE
        assert result.percentile < 25.0


class TestEnvironmentalEscalation:
    def test_two_or_more_factors_escalates_tier_by_one_step(self):
        alleles = [_make_allele("rs1", 0.3, 0.5)]
        dosages = [AlleleDosage(allele=alleles[0], dosage=1)]  # ~Average tier
        profile = PolygenicProfile(
            disorder="Type 2 Diabetes",
            dosages=dosages,
            environmental_factors=[
                EnvironmentalFactor.OBESITY,
                EnvironmentalFactor.SEDENTARY_LIFESTYLE,
            ],
        )
        result = calculate_polygenic_risk(profile)
        assert result.escalated is True
        assert result.final_tier != result.genetic_tier

    def test_single_factor_does_not_escalate(self):
        alleles = [_make_allele("rs1", 0.3, 0.5)]
        dosages = [AlleleDosage(allele=alleles[0], dosage=1)]
        profile = PolygenicProfile(
            disorder="Type 2 Diabetes",
            dosages=dosages,
            environmental_factors=[EnvironmentalFactor.OBESITY],
        )
        result = calculate_polygenic_risk(profile)
        assert result.escalated is False
        assert result.final_tier == result.genetic_tier

    def test_escalation_from_high_tier_stays_at_high_ceiling(self):
        # Already at HIGH — escalation must not go out of bounds.
        alleles = [_make_allele("rs1", 0.9, 0.05)]
        dosages = [AlleleDosage(allele=alleles[0], dosage=2)]
        profile = PolygenicProfile(
            disorder="Coronary Heart Disease",
            dosages=dosages,
            environmental_factors=[
                EnvironmentalFactor.SMOKING,
                EnvironmentalFactor.FAMILY_HISTORY,
            ],
        )
        result = calculate_polygenic_risk(profile)
        assert result.genetic_tier == RiskTier.HIGH
        assert result.final_tier == RiskTier.HIGH
        assert result.escalated is False   # already at ceiling, no step to escalate to


class TestDegenerateZeroVarianceCase:
    def test_zero_variance_returns_average_without_dividing_by_zero(self):
        # Allele frequency of exactly 1.0 -> variance term 2*af*(1-af) = 0
        allele = _make_allele("rs1", 0.5, 1.0)
        dosages = [AlleleDosage(allele=allele, dosage=2)]
        profile = PolygenicProfile(disorder="Type 2 Diabetes", dosages=dosages)
        result = calculate_polygenic_risk(profile)   # must not raise ZeroDivisionError
        assert result.genetic_tier == RiskTier.AVERAGE
        assert result.percentile == 50.0
        assert result.z_score == 0.0


class TestRationaleAndGovernanceLanguage:
    def test_rationale_states_relative_percentile_not_diagnosis(self):
        alleles = [_make_allele("rs1", 0.3, 0.5)]
        dosages = [AlleleDosage(allele=alleles[0], dosage=1)]
        profile = PolygenicProfile(disorder="Type 2 Diabetes", dosages=dosages)
        result = calculate_polygenic_risk(profile)
        assert any("not an individual diagnosis" in line for line in result.rationale)


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))