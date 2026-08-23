"""
Module 11 — HELIX: Chromosomal sub-model regression tests

Run: pytest test_chromosomal_model.py -v
"""

import pytest

from src.models.chromosomal_model import (
    KaryotypePattern,
    MatchConfidence,
    classify_karyotype,
)


class TestFullKaryotypeMatches:
    def test_trisomy_21_female(self):
        result = classify_karyotype("47,XX,+21")
        assert result.pattern == KaryotypePattern.TRISOMY_21
        assert result.disorder == "Down Syndrome"
        assert result.confidence == MatchConfidence.FULL
        assert result.mosaic_percentage is None

    def test_trisomy_21_male(self):
        result = classify_karyotype("47,XY,+21")
        assert result.pattern == KaryotypePattern.TRISOMY_21
        assert result.disorder == "Down Syndrome"

    def test_monosomy_x_turner(self):
        result = classify_karyotype("45,X")
        assert result.pattern == KaryotypePattern.MONOSOMY_X
        assert result.disorder == "Turner Syndrome"
        assert result.confidence == MatchConfidence.FULL

    def test_klinefelter(self):
        result = classify_karyotype("47,XXY")
        assert result.pattern == KaryotypePattern.KLINEFELTER
        assert result.disorder == "Klinefelter Syndrome"

    def test_normal_female_karyotype(self):
        result = classify_karyotype("46,XX")
        assert result.pattern == KaryotypePattern.NORMAL_46XX
        assert result.disorder == "No chromosomal abnormality detected"

    def test_normal_male_karyotype(self):
        result = classify_karyotype("46,XY")
        assert result.pattern == KaryotypePattern.NORMAL_46XY


class TestMosaicKaryotypeMatches:
    def test_high_percentage_mosaic_trisomy_21(self):
        result = classify_karyotype("47,XX,+21[80]/46,XX[20]")
        assert result.pattern == KaryotypePattern.TRISOMY_21
        assert result.disorder == "Down Syndrome"
        assert result.confidence == MatchConfidence.MOSAIC_HIGH
        assert result.mosaic_percentage == 80.0

    def test_low_percentage_mosaic_trisomy_21(self):
        result = classify_karyotype("47,XX,+21[30]/46,XX[70]")
        assert result.pattern == KaryotypePattern.TRISOMY_21
        assert result.confidence == MatchConfidence.MOSAIC_LOW
        assert result.mosaic_percentage == 30.0

    def test_mosaic_confidence_boundary_at_50_percent(self):
        # Exactly 50% should classify as HIGH (>=50), not LOW — boundary
        # behavior worth locking down explicitly.
        result = classify_karyotype("45,X[50]/46,XX[50]")
        assert result.confidence == MatchConfidence.MOSAIC_HIGH
        assert result.mosaic_percentage == 50.0

    def test_mosaic_rationale_notes_variable_expression(self):
        result = classify_karyotype("47,XX,+21[80]/46,XX[20]")
        assert any("mosaic" in line.lower() for line in result.rationale)


class TestUnrecognizedKaryotypes:
    """
    Anything outside the curated pattern set must return no match rather
    than a best-effort guess — a silently wrong chromosomal call is worse
    than an honest "unrecognized."
    """

    def test_completely_unrecognized_string_returns_no_match(self):
        result = classify_karyotype("99,ZZ,+99")
        assert result.pattern is None
        assert result.confidence == MatchConfidence.NONE
        assert result.disorder == "Unrecognized karyotype"

    def test_mosaic_with_unrecognized_abnormal_cell_line_returns_no_match(self):
        result = classify_karyotype("99,ZZ,+99[60]/46,XX[40]")
        assert result.pattern is None
        assert result.confidence == MatchConfidence.NONE
        # Mosaic percentage should still be captured even on no-match,
        # since it was successfully parsed even though the pattern wasn't recognized.
        assert result.mosaic_percentage == 60.0

    def test_empty_string_returns_no_match(self):
        result = classify_karyotype("")
        assert result.pattern is None
        assert result.confidence == MatchConfidence.NONE

    def test_malformed_mosaic_notation_falls_through_to_plain_no_match(self):
        result = classify_karyotype("47,XX,+21[80/46,XX[20]")  # missing closing bracket
        assert result.pattern is None
        assert result.confidence == MatchConfidence.NONE


class TestWhitespaceHandling:
    def test_leading_trailing_whitespace_is_stripped(self):
        result = classify_karyotype("  47,XX,+21  ")
        assert result.pattern == KaryotypePattern.TRISOMY_21


class TestRationaleExplainability:
    def test_rationale_always_present(self):
        for karyotype in ["47,XX,+21", "45,X", "99,ZZ,+99", ""]:
            result = classify_karyotype(karyotype)
            assert len(result.rationale) >= 1


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))