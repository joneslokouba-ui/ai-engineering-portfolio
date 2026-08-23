"""
Module 11 — HELIX: X-linked Sub-Model
========================================
Extends the Monogenic ensemble (consequence severity + conservation +
review-status confidence + allele-frequency dampener) with a sex-linked
inheritance layer, per ADR 011: "Monogenic-style scoring + sex-linked
inheritance logic."

Why this can't just reuse monogenic_model.py directly: X-linked recessive
disorders (e.g. Duchenne Muscular Dystrophy, Hemophilia A) express
differently by sex. A male with one X chromosome is hemizygous — a single
pathogenic variant is sufficient for full disease expression. A female
with two X chromosomes is typically an unaffected carrier unless she
inherits the variant on both copies (rare) or has skewed X-inactivation
(a real but harder-to-model phenomenon, out of scope here per ADR — see
module README limitations).

This module deliberately reuses the same variant-level scoring engine as
Monogenic (identical VariantFeatures shape, identical base score
mechanics) and adds a distinct expression/carrier-status output layer on
top — the point being that the underlying variant pathogenicity logic is
genuinely shared, while the clinical interpretation of that score is not.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.models.monogenic_model import (
    ClassificationResult,
    ConsequenceType,
    ReviewStatus,
    Tier,
    VariantFeatures,
    classify_monogenic_variant,
)


class Zygosity(str, Enum):
    HEMIZYGOUS = "hemizygous"      # one X allele present (typically male)
    HETEROZYGOUS = "heterozygous"  # two X alleles, variant on one
    HOMOZYGOUS = "homozygous"      # two X alleles, variant on both


class ExpressionStatus(str, Enum):
    AFFECTED = "Affected"
    CARRIER_UNAFFECTED = "Carrier (typically unaffected)"
    CARRIER_VARIABLE_EXPRESSION = "Carrier (variable expression possible — skewed X-inactivation)"
    NOT_APPLICABLE = "Not applicable — variant tier does not support a call"


@dataclass
class XLinkedFeatures:
    variant: VariantFeatures
    zygosity: Zygosity

    def __post_init__(self) -> None:
        if self.zygosity == Zygosity.HOMOZYGOUS and self.variant.gene == "":
            raise ValueError("gene must be specified for zygosity determination")


@dataclass
class XLinkedResult:
    variant_classification: ClassificationResult
    expression_status: ExpressionStatus
    rationale: list[str]

    @property
    def tier(self) -> Tier:
        return self.variant_classification.tier


def _determine_expression_status(tier: Tier, zygosity: Zygosity) -> tuple[ExpressionStatus, str]:
    """
    Sex-linked inheritance logic layer: maps (variant tier, zygosity) to
    an expected expression/carrier status. This is the piece that has no
    equivalent in monogenic_model.py.
    """
    if tier != Tier.PATHOGENIC:
        return ExpressionStatus.NOT_APPLICABLE, (
            f"Variant tier is {tier.value}, not Pathogenic — expression "
            f"status calls require a confident pathogenic classification "
            f"first."
        )

    if zygosity == Zygosity.HEMIZYGOUS:
        return ExpressionStatus.AFFECTED, (
            "Hemizygous (single X allele) with a Pathogenic variant — "
            "full disease expression expected, no second allele to "
            "compensate."
        )
    if zygosity == Zygosity.HOMOZYGOUS:
        return ExpressionStatus.AFFECTED, (
            "Homozygous — Pathogenic variant present on both X alleles, "
            "full disease expression expected (rare for X-linked "
            "recessive disorders, but fully penetrant when it occurs)."
        )
    # HETEROZYGOUS
    return ExpressionStatus.CARRIER_VARIABLE_EXPRESSION, (
        "Heterozygous — typically an unaffected carrier under X-linked "
        "recessive inheritance, but skewed X-inactivation can produce "
        "variable symptomatic expression. This module flags the "
        "possibility rather than modeling X-inactivation skew directly "
        "(explicit scope limitation, see module README)."
    )


def classify_xlinked_variant(features: XLinkedFeatures) -> XLinkedResult:
    """
    Classifies an X-linked variant by first running the shared Monogenic
    scoring engine, then layering sex-linked expression logic on top of
    the resulting tier.
    """
    variant_result = classify_monogenic_variant(features.variant)
    expression_status, expression_rationale = _determine_expression_status(
        variant_result.tier, features.zygosity
    )

    rationale = list(variant_result.rationale)
    rationale.append(expression_rationale)

    return XLinkedResult(
        variant_classification=variant_result,
        expression_status=expression_status,
        rationale=rationale,
    )