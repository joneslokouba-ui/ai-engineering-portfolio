"""
Module 11 — HELIX: gnomAD Loader
===================================
Parses a gnomAD-format population allele frequency CSV extract into a
lookup table keyed by (gene, variant_name), for merging with ClinVar
records to produce complete VariantFeatures (monogenic_model.py).

Real gnomAD access is via their public downloads or GraphQL API — per
ADR 011, this loader targets a static curated CSV extract rather than a
live API dependency, keeping the pipeline offline-reproducible.
"""

from __future__ import annotations

import csv
from pathlib import Path


def load_gnomad_frequencies(filepath: str | Path) -> dict[tuple[str, str], float]:
    """
    Parses a gnomAD-format CSV (GeneSymbol, VariantName, AlleleFrequency)
    into a {(gene, variant_name): allele_frequency} lookup.

    Raises ValueError if any AlleleFrequency value can't be parsed as a
    float, or falls outside [0.0, 1.0] — a malformed frequency should
    fail loudly rather than silently propagate a nonsensical value into
    downstream classification.
    """
    filepath = Path(filepath)
    lookup: dict[tuple[str, str], float] = {}

    with filepath.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):  # header is row 1
            gene = row["GeneSymbol"].strip()
            variant_name = row["VariantName"].strip()
            try:
                af = float(row["AlleleFrequency"])
            except ValueError as e:
                raise ValueError(
                    f"gnomAD row {row_num}: could not parse AlleleFrequency "
                    f"'{row['AlleleFrequency']}' as a float."
                ) from e
            if not 0.0 <= af <= 1.0:
                raise ValueError(
                    f"gnomAD row {row_num}: AlleleFrequency {af} outside "
                    f"valid range [0.0, 1.0]."
                )
            lookup[(gene, variant_name)] = af

    return lookup