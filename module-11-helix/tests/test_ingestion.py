"""
Module 11 — HELIX: Ingestion layer regression tests

Run: pytest test_ingestion.py -v
"""

import pytest

from src.ingestion.clinvar_loader import load_clinvar_records
from src.ingestion.gnomad_loader import load_gnomad_frequencies
from src.models.monogenic_model import ConsequenceType, ReviewStatus
from src.ingestion.omim_loader import load_omim_knowledge
from src.ingestion.variant_feature_builder import build_variant_features, normalize_variant_name

from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


class TestClinVarLoader:
    def test_loads_all_rows_without_gene_filter(self):
        records = load_clinvar_records(f"{FIXTURES}/clinvar_sample.tsv")
        assert len(records) == 10

    def test_gene_panel_filter_restricts_results(self):
        records = load_clinvar_records(f"{FIXTURES}/clinvar_sample.tsv", gene_panel={"CFTR"})
        assert len(records) == 2
        assert all(r.gene == "CFTR" for r in records)

    def test_frameshift_inference_from_fs_notation(self):
        records = load_clinvar_records(f"{FIXTURES}/clinvar_sample.tsv", gene_panel={"DMD"})
        frameshift_record = next(r for r in records if "Pro88fs" in r.variant_name)
        assert frameshift_record.inferred_consequence == ConsequenceType.FRAMESHIFT

    def test_nonsense_inference_from_ter_notation(self):
        records = load_clinvar_records(f"{FIXTURES}/clinvar_sample.tsv", gene_panel={"F8"})
        nonsense_record = next(r for r in records if "Arg2016Ter" in r.variant_name)
        assert nonsense_record.inferred_consequence == ConsequenceType.NONSENSE

    def test_synonymous_inference_from_equals_notation(self):
        records = load_clinvar_records(f"{FIXTURES}/clinvar_sample.tsv", gene_panel={"DMD"})
        synonymous_record = next(r for r in records if "Leu399=" in r.variant_name)
        assert synonymous_record.inferred_consequence == ConsequenceType.SYNONYMOUS

    def test_in_frame_deletion_inference_for_cftr_f508del(self):
        # Regression guard for a real bug: p.Phe508del (CFTR ΔF508, the
        # single most common CF-causing variant) was initially left
        # unclassified because the inference patterns didn't cover
        # del/dup/ins without 'fs'. Locking this down explicitly.
        records = load_clinvar_records(f"{FIXTURES}/clinvar_sample.tsv", gene_panel={"CFTR"})
        f508del_record = next(r for r in records if "Phe508del" in r.variant_name)
        assert f508del_record.inferred_consequence == ConsequenceType.IN_FRAME_INDEL

    def test_missense_inference_from_substitution_notation(self):
        records = load_clinvar_records(f"{FIXTURES}/clinvar_sample.tsv", gene_panel={"HBB"})
        missense_record = next(r for r in records if "Glu7Val" in r.variant_name)
        assert missense_record.inferred_consequence == ConsequenceType.MISSENSE

    def test_splice_inference_from_intronic_offset_notation(self):
        records = load_clinvar_records(f"{FIXTURES}/clinvar_sample.tsv", gene_panel={"HBB"})
        splice_record = next(r for r in records if "315+1G>A" in r.variant_name)
        assert splice_record.inferred_consequence == ConsequenceType.SPLICE_SITE

    def test_review_status_mapped_correctly(self):
        records = load_clinvar_records(f"{FIXTURES}/clinvar_sample.tsv", gene_panel={"CFTR"})
        expert_panel_record = next(r for r in records if "Phe508del" in r.variant_name)
        assert expert_panel_record.review_status == ReviewStatus.EXPERT_PANEL

    def test_not_provided_phenotype_is_excluded_from_list(self):
        records = load_clinvar_records(f"{FIXTURES}/clinvar_sample.tsv", gene_panel={"DMD"})
        benign_record = next(r for r in records if "Leu399=" in r.variant_name)
        assert benign_record.phenotypes == []

    def test_real_phenotype_is_captured(self):
        records = load_clinvar_records(f"{FIXTURES}/clinvar_sample.tsv", gene_panel={"CFTR"})
        assert "Cystic fibrosis" in records[0].phenotypes


class TestGnomadLoader:
    def test_loads_all_rows(self):
        lookup = load_gnomad_frequencies(f"{FIXTURES}/gnomad_sample.csv")
        assert len(lookup) == 10

    def test_specific_frequency_parsed_correctly(self):
        lookup = load_gnomad_frequencies(f"{FIXTURES}/gnomad_sample.csv")
        assert lookup[("CFTR", "c.1521_1523delCTT (p.Phe508del)")] == pytest.approx(0.0000180)

    def test_common_variant_frequency_parsed_correctly(self):
        lookup = load_gnomad_frequencies(f"{FIXTURES}/gnomad_sample.csv")
        assert lookup[("F8", "c.870A>G (p.Ala290=)")] == pytest.approx(0.0510000)


class TestOmimLoader:
    def test_loads_all_disorders(self):
        knowledge = load_omim_knowledge(f"{FIXTURES}/omim_sample.csv")
        assert len(knowledge) == 3
        assert "Cystic Fibrosis" in knowledge

    def test_sections_shape_matches_rag_stub_convention(self):
        knowledge = load_omim_knowledge(f"{FIXTURES}/omim_sample.csv")
        sections = knowledge["Cystic Fibrosis"].as_sections()
        assert set(sections.keys()) == {
            "Causes & Inheritance", "Prevalence", "Research & Advances", "Clinical Applications"
        }
        assert "CFTR" in sections["Causes & Inheritance"]


class TestVariantNameNormalization:
    """
    Regression coverage for a real bug caught during initial testing:
    ClinVar's Name field carries a transcript prefix that gnomAD/
    conservation extracts don't, silently breaking every join until
    normalized. Locking this down directly so it can't regress.
    """

    def test_strips_transcript_prefix(self):
        assert (
            normalize_variant_name("NM_000492.4(CFTR):c.1521_1523delCTT (p.Phe508del)")
            == "c.1521_1523delCTT (p.Phe508del)"
        )

    def test_leaves_already_bare_name_unchanged(self):
        assert normalize_variant_name("c.315+1G>A") == "c.315+1G>A"


class TestVariantFeatureBuilderMergesAllThreeSources:
    def test_variants_with_full_data_are_built_successfully(self):
        clinvar_records = load_clinvar_records(f"{FIXTURES}/clinvar_sample.tsv", gene_panel={"CFTR"})
        gnomad_lookup = load_gnomad_frequencies(f"{FIXTURES}/gnomad_sample.csv")
        conservation_lookup = {
            ("CFTR", "c.1521_1523delCTT (p.Phe508del)"): 0.9,
            ("CFTR", "c.350G>A (p.Arg117His)"): 0.6,
        }
        built, unbuildable = build_variant_features(clinvar_records, gnomad_lookup, conservation_lookup)
        assert len(built) == 2
        assert len(unbuildable) == 0
        assert built[0].gene == "CFTR"

    def test_variant_missing_gnomad_match_is_reported_not_dropped_silently(self):
        clinvar_records = load_clinvar_records(f"{FIXTURES}/clinvar_sample.tsv", gene_panel={"CFTR"})
        empty_gnomad: dict = {}
        conservation_lookup = {
            ("CFTR", "c.1521_1523delCTT (p.Phe508del)"): 0.9,
        }
        built, unbuildable = build_variant_features(clinvar_records, empty_gnomad, conservation_lookup)
        assert len(built) == 0
        assert len(unbuildable) == 2
        assert all("gnomAD" in u.reason for u in unbuildable)

    def test_variant_missing_conservation_score_is_reported(self):
        clinvar_records = load_clinvar_records(f"{FIXTURES}/clinvar_sample.tsv", gene_panel={"CFTR"})
        gnomad_lookup = load_gnomad_frequencies(f"{FIXTURES}/gnomad_sample.csv")
        empty_conservation: dict = {}
        built, unbuildable = build_variant_features(clinvar_records, gnomad_lookup, empty_conservation)
        assert len(built) == 0
        assert all("conservation" in u.reason.lower() for u in unbuildable)

    def test_built_features_are_directly_usable_by_monogenic_model(self):
        from src.models.monogenic_model import classify_monogenic_variant

        clinvar_records = load_clinvar_records(f"{FIXTURES}/clinvar_sample.tsv", gene_panel={"HBB"})
        gnomad_lookup = load_gnomad_frequencies(f"{FIXTURES}/gnomad_sample.csv")
        conservation_lookup = {
            ("HBB", "c.20A>T (p.Glu7Val)"): 0.9,
            ("HBB", "c.315+1G>A"): 0.85,
        }
        built, unbuildable = build_variant_features(clinvar_records, gnomad_lookup, conservation_lookup)
        assert len(built) == 2
        # End-to-end: real ingested data flows straight into the sub-model
        # built earlier in the session without any adaptation needed.
        for features in built:
            result = classify_monogenic_variant(features)
            assert result.tier is not None


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))