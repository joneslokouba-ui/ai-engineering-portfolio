"""
Module 11 — HELIX: Curated gene panel consistency tests

Verifies that data/processed/curated_gene_panel.csv — intended as the
authoritative source for which genes/disorders HELIX covers — actually
agrees with what's hardcoded in each sub-model. Without this check, the
panel CSV and the sub-models' internal lookup tables (KNOWN_VARIANTS,
KARYOTYPE_LOOKUP, etc.) could silently drift apart as either side is
edited independently.

Run: pytest test_curated_gene_panel.py -v
"""

import csv
from pathlib import Path

import pytest

from src.models.chromosomal_model import KARYOTYPE_LOOKUP
from src.models.mitochondrial_model import KNOWN_VARIANTS

PANEL_PATH = Path(__file__).parent.parent / "data" / "processed" / "curated_gene_panel.csv"


def _load_panel() -> list[dict]:
    with PANEL_PATH.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class TestPanelStructure:
    def test_panel_covers_all_five_categories(self):
        rows = _load_panel()
        categories = {row["Category"] for row in rows}
        assert categories == {
            "Monogenic", "Chromosomal", "Multifactorial", "X-linked", "Mitochondrial"
        }

    def test_no_blank_required_fields(self):
        rows = _load_panel()
        for row in rows:
            for field in ("Category", "Gene_Or_Locus", "Disorder", "Inheritance_Pattern"):
                assert row[field].strip(), f"Blank {field} in row: {row}"


class TestMitochondrialConsistency:
    """
    Every mitochondrial disorder listed in the panel must have a matching
    entry in mitochondrial_model.KNOWN_VARIANTS, and vice versa — the
    panel and the model's actual lookup table must agree on which
    mitochondrial variants HELIX can classify.
    """

    def test_panel_mitochondrial_disorders_match_known_variants(self):
        rows = [r for r in _load_panel() if r["Category"] == "Mitochondrial"]
        panel_disorders = {r["Disorder"] for r in rows}
        model_disorders = {v.disorder for v in KNOWN_VARIANTS.values()}
        assert panel_disorders == model_disorders, (
            f"Panel lists {panel_disorders}, but mitochondrial_model.py's "
            f"KNOWN_VARIANTS covers {model_disorders} — these must match "
            f"or the panel is misrepresenting what the model actually does."
        )

    def test_panel_reference_variants_exist_in_model(self):
        rows = [r for r in _load_panel() if r["Category"] == "Mitochondrial"]
        for row in rows:
            variant_id = row["Reference_Variant_Or_Pattern"]
            assert variant_id in KNOWN_VARIANTS, (
                f"Panel references variant '{variant_id}' for "
                f"{row['Disorder']}, but it's not in "
                f"mitochondrial_model.KNOWN_VARIANTS."
            )


class TestChromosomalConsistency:
    def test_panel_chromosomal_disorders_match_karyotype_lookup(self):
        rows = [r for r in _load_panel() if r["Category"] == "Chromosomal"]
        panel_disorders = {r["Disorder"] for r in rows}
        model_disorders = {
            entry.disorder for pattern, entry in KARYOTYPE_LOOKUP.items()
            if entry.disorder != "No chromosomal abnormality detected"
        }
        assert panel_disorders.issubset(model_disorders), (
            f"Panel lists chromosomal disorders {panel_disorders} not all "
            f"present in chromosomal_model.py's KARYOTYPE_LOOKUP "
            f"({model_disorders})."
        )


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))