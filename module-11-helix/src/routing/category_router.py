"""
Module 11 — HELIX: Category Router
=====================================
Dispatches an incoming case to the correct sub-model (per ADR 011 /
helix_architecture.mmd) and normalizes the five heterogeneous result
types — ClassificationResult, XLinkedResult, ChromosomalResult,
MultifactorialResult, MitochondrialResult — into one common
RoutedCaseResult shape that the dashboard and simulation can consume
without needing to know which of the five sub-models produced it.

This is the piece that turns five independently-correct sub-models into
one coherent pipeline. Each sub-model's input shape is genuinely
different (a scored variant, a variant + zygosity, a karyotype string, a
polygenic profile, a variant ID + heteroplasmy percentage) — the router
does not try to paper over that with a fake shared input type. Instead
it accepts a discriminated union (CaseInput) and narrows on `.category`
before dispatch, which keeps each sub-model's real input contract intact.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from src.models.chromosomal_model import ChromosomalResult, classify_karyotype
from src.models.mitochondrial_model import MitochondrialResult, classify_mitochondrial_variant
from src.models.monogenic_model import ClassificationResult, VariantFeatures, classify_monogenic_variant
from src.models.multifactorial_model import (
    MultifactorialResult,
    PolygenicProfile,
    calculate_polygenic_risk,
)
from sim.intake_pipeline_sim import Category
from src.models.xlinked_model import XLinkedFeatures, XLinkedResult, classify_xlinked_variant


# ---------------------------------------------------------------------------
# Discriminated union of per-category case inputs
# ---------------------------------------------------------------------------

@dataclass
class MonogenicCase:
    category: Category = Category.MONOGENIC
    features: VariantFeatures = None  # type: ignore[assignment]


@dataclass
class XLinkedCase:
    category: Category = Category.XLINKED
    features: XLinkedFeatures = None  # type: ignore[assignment]


@dataclass
class ChromosomalCase:
    category: Category = Category.CHROMOSOMAL
    karyotype: str = ""


@dataclass
class MultifactorialCase:
    category: Category = Category.MULTIFACTORIAL
    profile: PolygenicProfile = None  # type: ignore[assignment]


@dataclass
class MitochondrialCase:
    category: Category = Category.MITOCHONDRIAL
    variant_id: str = ""
    heteroplasmy_pct: float = 0.0


CaseInput = Union[
    MonogenicCase, XLinkedCase, ChromosomalCase, MultifactorialCase, MitochondrialCase
]

SubModelResult = Union[
    ClassificationResult, XLinkedResult, ChromosomalResult, MultifactorialResult, MitochondrialResult
]


# ---------------------------------------------------------------------------
# Normalized output
# ---------------------------------------------------------------------------

@dataclass
class RoutedCaseResult:
    category: Category
    summary_label: str          # normalized, human-readable headline result
    matched: bool                # False = no confident call (VUS, unrecognized, degenerate)
    raw_result: SubModelResult   # the original sub-model-specific result object
    rationale: list[str]


class UnroutableCaseError(Exception):
    """Raised when a CaseInput's category doesn't match its own payload type."""


def _summarize_monogenic(result: ClassificationResult) -> tuple[str, bool]:
    return result.tier.value, result.tier.value != "VUS"


def _summarize_xlinked(result: XLinkedResult) -> tuple[str, bool]:
    if result.tier.value == "VUS":
        return "VUS", False
    return f"{result.tier.value} — {result.expression_status.value}", True


def _summarize_chromosomal(result: ChromosomalResult) -> tuple[str, bool]:
    if not result.pattern:
        return "Unrecognized karyotype", False
    return result.disorder, True


def _summarize_multifactorial(result: MultifactorialResult) -> tuple[str, bool]:
    return f"{result.final_tier.value} ({result.percentile:.1f}th percentile)", True


def _summarize_mitochondrial(result: MitochondrialResult) -> tuple[str, bool]:
    if not result.matched:
        return "Unrecognized variant", False
    return f"{result.disorder} — {result.expression_tier.value}", True


def route_case(case: CaseInput) -> RoutedCaseResult:
    """
    Dispatches a case to its category's sub-model and normalizes the
    result. Raises UnroutableCaseError if the case's declared category
    doesn't match its own payload — this guards against a caller
    constructing e.g. a MonogenicCase but manually overriding `.category`
    to something else, which would otherwise silently call the wrong model.
    """
    if isinstance(case, MonogenicCase):
        if case.category != Category.MONOGENIC:
            raise UnroutableCaseError(
                f"MonogenicCase declared category={case.category}, expected MONOGENIC"
            )
        result = classify_monogenic_variant(case.features)
        label, matched = _summarize_monogenic(result)
        return RoutedCaseResult(Category.MONOGENIC, label, matched, result, result.rationale)

    if isinstance(case, XLinkedCase):
        if case.category != Category.XLINKED:
            raise UnroutableCaseError(
                f"XLinkedCase declared category={case.category}, expected XLINKED"
            )
        result = classify_xlinked_variant(case.features)
        label, matched = _summarize_xlinked(result)
        return RoutedCaseResult(Category.XLINKED, label, matched, result, result.rationale)

    if isinstance(case, ChromosomalCase):
        if case.category != Category.CHROMOSOMAL:
            raise UnroutableCaseError(
                f"ChromosomalCase declared category={case.category}, expected CHROMOSOMAL"
            )
        result = classify_karyotype(case.karyotype)
        label, matched = _summarize_chromosomal(result)
        return RoutedCaseResult(Category.CHROMOSOMAL, label, matched, result, result.rationale)

    if isinstance(case, MultifactorialCase):
        if case.category != Category.MULTIFACTORIAL:
            raise UnroutableCaseError(
                f"MultifactorialCase declared category={case.category}, expected MULTIFACTORIAL"
            )
        result = calculate_polygenic_risk(case.profile)
        label, matched = _summarize_multifactorial(result)
        return RoutedCaseResult(Category.MULTIFACTORIAL, label, matched, result, result.rationale)

    if isinstance(case, MitochondrialCase):
        if case.category != Category.MITOCHONDRIAL:
            raise UnroutableCaseError(
                f"MitochondrialCase declared category={case.category}, expected MITOCHONDRIAL"
            )
        result = classify_mitochondrial_variant(case.variant_id, case.heteroplasmy_pct)
        label, matched = _summarize_mitochondrial(result)
        return RoutedCaseResult(Category.MITOCHONDRIAL, label, matched, result, result.rationale)

    raise UnroutableCaseError(f"Unrecognized case input type: {type(case).__name__}")