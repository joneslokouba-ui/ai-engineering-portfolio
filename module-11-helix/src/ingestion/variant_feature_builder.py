"""
Module 11 — HELIX: Variant Feature Builder
=============================================
Merges ClinVarRecord (clinvar_loader.py) with gnomAD frequency data
(gnomad_loader.py) into real monogenic_model.VariantFeatures objects —
this is what finally replaces case_generator.py's random synthetic
features with genuine (if still portfolio-scoped) reference data.

Conservation score has no source in this build (real deployment would
use phyloP/GERP from UCSC or a similar track) — this builder requires it
to be supplied explicitly per variant rather than fabricating one, since
inventing a conservation score would be worse than declining to classify.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.ingestion.clinvar_loader import ClinVarRecord
from src.models.monogenic_model import VariantFeatures

# ClinVar's Name field includes a transcript prefix, e.g.
#   "NM_000492.4(CFTR):c.1521_1523delCTT (p.Phe508del)"
# while gnomAD/conservation extracts key on the bare HGVS suffix, e.g.
#   "c.1521_1523delCTT (p.Phe508del)"
# This was caught as a real bug during initial testing: the two sources'
# naming conventions don't match, so a direct (gene, name) join silently
# failed for every variant. Normalizing to the "c.*" suffix here fixes
# the join without requiring gnomad_loader.py or the fixture data to
# adopt ClinVar's transcript-prefixed convention.
_TRANSCRIPT_PREFIX_RE = re.compile(r"^[^:]+:(c\..*)$")


def normalize_variant_name(name: str) -> str:
    """Strips a leading transcript accession/gene prefix (e.g.
    'NM_000492.4(CFTR):') from a ClinVar-style variant name, leaving the
    bare 'c.*' HGVS suffix used as the join key with gnomAD/conservation
    lookups. Names that don't match the prefixed pattern are returned
    unchanged."""
    match = _TRANSCRIPT_PREFIX_RE.match(name)
    return match.group(1) if match else name


@dataclass
class UnbuildableVariant:
    """Represents a ClinVar record that could not be turned into
    VariantFeatures, with the reason why — surfaced to the caller instead
    of silently dropping records."""
    record: ClinVarRecord
    reason: str


def build_variant_features(
    clinvar_records: list[ClinVarRecord],
    gnomad_lookup: dict[tuple[str, str], float],
    conservation_lookup: dict[tuple[str, str], float],
) -> tuple[list[VariantFeatures], list[UnbuildableVariant]]:
    """
    Merges ClinVar + gnomAD + conservation data into VariantFeatures.

    Returns (built, unbuildable) rather than raising on the first gap —
    a real curated panel will have some variants without a gnomAD match
    (too rare to appear) or without a conservation score; those should be
    reported, not silently skipped or silently defaulted, so a caller can
    decide how to handle the gap (e.g. treat missing gnomAD AF as
    effectively zero for a variant absent from a population database —
    but that is a judgment call left to the caller, not this function).
    """
    built: list[VariantFeatures] = []
    unbuildable: list[UnbuildableVariant] = []

    for record in clinvar_records:
        key = (record.gene, normalize_variant_name(record.variant_name))

        if record.inferred_consequence is None:
            unbuildable.append(
                UnbuildableVariant(
                    record=record,
                    reason=f"No consequence type could be inferred: {record.consequence_inference_note}",
                )
            )
            continue

        if key not in gnomad_lookup:
            unbuildable.append(
                UnbuildableVariant(
                    record=record,
                    reason="No matching gnomAD allele frequency record found.",
                )
            )
            continue

        if key not in conservation_lookup:
            unbuildable.append(
                UnbuildableVariant(
                    record=record,
                    reason="No conservation score available for this variant.",
                )
            )
            continue

        built.append(
            VariantFeatures(
                gene=record.gene,
                consequence=record.inferred_consequence,
                review_status=record.review_status,
                conservation_score=conservation_lookup[key],
                gnomad_allele_frequency=gnomad_lookup[key],
            )
        )

    return built, unbuildable