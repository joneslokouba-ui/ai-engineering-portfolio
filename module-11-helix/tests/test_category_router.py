"""
Module 11 — HELIX: Category router regression tests

Run: pytest test_category_router.py -v
"""

import pytest

from src.routing.category_router import (
    ChromosomalCase,
    MitochondrialCase,
    MonogenicCase,
    MultifactorialCase,
    UnroutableCaseError,
    XLinkedCase,
    route_case,
)
from src.models.monogenic_model import ConsequenceType, ReviewStatus, VariantFeatures
from src.models.multifactorial_model import AlleleDosage, PolygenicProfile, RiskAllele
from sim.intake_pipeline_sim import Category
from src.models.xlinked_model import XLinkedFeatures, Zygosity


def _pathogenic_variant() -> VariantFeatures:
    return VariantFeatures(
        gene="HTT",
        consequence=ConsequenceType.FRAMESHIFT,
        review_status=ReviewStatus.EXPERT_PANEL,
        conservation_score=0.95,
        gnomad_allele_frequency=0.00001,
    )


class TestMonogenicRouting:
    def test_routes_to_monogenic_and_returns_pathogenic_summary(self):
        case = MonogenicCase(features=_pathogenic_variant())
        result = route_case(case)
        assert result.category == Category.MONOGENIC
        assert result.summary_label == "Pathogenic"
        assert result.matched is True
        assert len(result.rationale) > 0

    def test_vus_variant_reports_unmatched(self):
        vus_features = VariantFeatures(
            gene="HBB",
            consequence=ConsequenceType.MISSENSE,
            review_status=ReviewStatus.MULTIPLE_SUBMITTERS,
            conservation_score=0.5,
            gnomad_allele_frequency=0.002,
        )
        case = MonogenicCase(features=vus_features)
        result = route_case(case)
        assert result.summary_label == "VUS"
        assert result.matched is False


class TestXLinkedRouting:
    def test_routes_to_xlinked_and_includes_expression_status(self):
        case = XLinkedCase(
            features=XLinkedFeatures(
                variant=_pathogenic_variant(), zygosity=Zygosity.HEMIZYGOUS
            )
        )
        result = route_case(case)
        assert result.category == Category.XLINKED
        assert "Affected" in result.summary_label
        assert result.matched is True


class TestChromosomalRouting:
    def test_routes_to_chromosomal_and_returns_disorder_name(self):
        case = ChromosomalCase(karyotype="47,XX,+21")
        result = route_case(case)
        assert result.category == Category.CHROMOSOMAL
        assert result.summary_label == "Down Syndrome"
        assert result.matched is True

    def test_unrecognized_karyotype_reports_unmatched(self):
        case = ChromosomalCase(karyotype="99,ZZ,+99")
        result = route_case(case)
        assert result.summary_label == "Unrecognized karyotype"
        assert result.matched is False


class TestMultifactorialRouting:
    def test_routes_to_multifactorial_and_returns_percentile_label(self):
        allele = RiskAllele(rsid="rs1", effect_weight=0.3, population_allele_frequency=0.5)
        profile = PolygenicProfile(
            disorder="Type 2 Diabetes",
            dosages=[AlleleDosage(allele=allele, dosage=1)],
        )
        case = MultifactorialCase(profile=profile)
        result = route_case(case)
        assert result.category == Category.MULTIFACTORIAL
        assert "percentile" in result.summary_label
        assert result.matched is True   # multifactorial always returns a tier, never "unmatched"


class TestMitochondrialRouting:
    def test_routes_to_mitochondrial_and_returns_disorder_and_tier(self):
        case = MitochondrialCase(variant_id="m.3243A>G", heteroplasmy_pct=70.0)
        result = route_case(case)
        assert result.category == Category.MITOCHONDRIAL
        assert "MELAS" in result.summary_label
        assert result.matched is True

    def test_unrecognized_mitochondrial_variant_reports_unmatched(self):
        case = MitochondrialCase(variant_id="m.9999X>Y", heteroplasmy_pct=50.0)
        result = route_case(case)
        assert result.summary_label == "Unrecognized variant"
        assert result.matched is False


class TestCategoryMismatchGuard:
    """
    A case whose .category has been manually overridden to disagree with
    its own payload type must be rejected, not silently routed to the
    wrong sub-model.
    """

    def test_monogenic_case_with_wrong_category_raises(self):
        case = MonogenicCase(features=_pathogenic_variant())
        case.category = Category.CHROMOSOMAL  # tampered after construction
        with pytest.raises(UnroutableCaseError):
            route_case(case)

    def test_chromosomal_case_with_wrong_category_raises(self):
        case = ChromosomalCase(karyotype="45,X")
        case.category = Category.MITOCHONDRIAL
        with pytest.raises(UnroutableCaseError):
            route_case(case)


class TestAllFiveCategoriesRouteWithoutCrossContamination:
    """
    Sends one case per category through the router and confirms each
    result's raw_result is an instance of the correct sub-model's result
    type — the strongest guard against a copy-paste dispatch bug that
    silently calls the wrong sub-model for a given category.
    """

    def test_each_category_returns_its_own_result_type(self):
        from src.models.chromosomal_model import ChromosomalResult
        from src.models.mitochondrial_model import MitochondrialResult
        from src.models.monogenic_model import ClassificationResult
        from src.models.multifactorial_model import MultifactorialResult
        from src.models.xlinked_model import XLinkedResult

        allele = RiskAllele(rsid="rs1", effect_weight=0.3, population_allele_frequency=0.5)

        cases_and_types = [
            (MonogenicCase(features=_pathogenic_variant()), ClassificationResult),
            (
                XLinkedCase(
                    features=XLinkedFeatures(
                        variant=_pathogenic_variant(), zygosity=Zygosity.HEMIZYGOUS
                    )
                ),
                XLinkedResult,
            ),
            (ChromosomalCase(karyotype="45,X"), ChromosomalResult),
            (
                MultifactorialCase(
                    profile=PolygenicProfile(
                        disorder="Type 2 Diabetes",
                        dosages=[AlleleDosage(allele=allele, dosage=1)],
                    )
                ),
                MultifactorialResult,
            ),
            (
                MitochondrialCase(variant_id="m.11778G>A", heteroplasmy_pct=80.0),
                MitochondrialResult,
            ),
        ]

        for case, expected_type in cases_and_types:
            result = route_case(case)
            assert isinstance(result.raw_result, expected_type), (
                f"{type(case).__name__} produced a {type(result.raw_result).__name__}, "
                f"expected {expected_type.__name__}"
            )


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))