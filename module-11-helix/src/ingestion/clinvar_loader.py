"""
Module 11 — HELIX: ClinVar Loader
====================================
Parses a ClinVar-format `variant_summary.txt`-style file (tab-separated,
subset of real ClinVar columns: GeneSymbol, Name, ClinicalSignificance,
ReviewStatus, PhenotypeList) into structured VariantRecord objects.

Real ClinVar exports do NOT include a clean "consequence type" column —
that typically comes from separate VEP/SnpEff annotation. Rather than
depend on an annotation tool unavailable in this environment, this loader
infers consequence type from the HGVS protein notation embedded in the
`Name` field (e.g. "p.Arg2016Ter" -> nonsense, "p.Pro88fs" -> frameshift).
This is a simplified proxy, not a substitute for real VEP annotation —
documented explicitly so it's never mistaken for one.

Output feeds monogenic_model.VariantFeatures once merged with gnomAD
allele frequency (gnomad_loader.py) and a conservation score (not yet
sourced — see module README limitations).
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from src.models.monogenic_model import ConsequenceType, ReviewStatus


@dataclass
class ClinVarRecord:
    gene: str
    variant_name: str            # HGVS notation, used as the join key with gnomAD
    clinical_significance: str   # raw ClinVar label — informational only, NOT used
                                  # as the classification output (that's the sub-model's job)
    review_status: ReviewStatus
    phenotypes: list[str]
    inferred_consequence: ConsequenceType | None
    consequence_inference_note: str


# Maps ClinVar's free-text ReviewStatus strings to the ReviewStatus enum
# used by monogenic_model.py. ClinVar's actual strings are used verbatim
# as dict keys, since that's what appears in real exports.
_REVIEW_STATUS_MAP: dict[str, ReviewStatus] = {
    "practice guideline": ReviewStatus.PRACTICE_GUIDELINE,
    "reviewed by expert panel": ReviewStatus.EXPERT_PANEL,
    "criteria provided, multiple submitters": ReviewStatus.MULTIPLE_SUBMITTERS,
    "criteria provided, single submitter": ReviewStatus.SINGLE_SUBMITTER,
    "no assertion criteria provided": ReviewStatus.NO_ASSERTION,
}

# HGVS protein notation patterns, checked in order of specificity.
# "Ter" or "*" indicates a stop codon (nonsense). "fs" indicates frameshift.
# "=" indicates the same amino acid (synonymous). "del"/"dup" WITHOUT "fs"
# indicates an in-frame indel (e.g. CFTR p.Phe508del — this pattern was
# added after initial testing missed it entirely; ΔF508 is the single
# most common CF-causing variant, so silently failing to classify it was
# a real bug, not an edge case worth ignoring). A single 3-letter-code
# substitution with no fs/Ter/=/del/dup is treated as missense. Splice
# variants are detected from the coding notation (c.) rather than protein
# notation, since intronic splice variants often have no protein-level
# HGVS at all.
_FRAMESHIFT_RE = re.compile(r"fs")
_NONSENSE_RE = re.compile(r"Ter|\*\)")
_SYNONYMOUS_RE = re.compile(r"p\.\w{3}\d+=")
_IN_FRAME_INDEL_RE = re.compile(r"p\.\w{3}\d+(_\w{3}\d+)?(del|dup|ins)")
_SPLICE_RE = re.compile(r"c\.\d+[+-]\d+")
_MISSENSE_RE = re.compile(r"p\.[A-Z][a-z]{2}\d+[A-Z][a-z]{2}")


def _infer_consequence(name: str) -> tuple[ConsequenceType | None, str]:
    """
    Infers ConsequenceType from an HGVS variant name string. Returns
    (consequence, note) — note explains the basis for the inference (or
    why none could be made), surfaced downstream for transparency rather
    than silently guessing.
    """
    if _SPLICE_RE.search(name):
        return ConsequenceType.SPLICE_SITE, "Inferred from intronic +/- coding offset notation."
    if _FRAMESHIFT_RE.search(name):
        return ConsequenceType.FRAMESHIFT, "Inferred from 'fs' in HGVS protein notation."
    if _NONSENSE_RE.search(name):
        return ConsequenceType.NONSENSE, "Inferred from stop-codon notation (Ter/*) in HGVS protein notation."
    if _SYNONYMOUS_RE.search(name):
        return ConsequenceType.SYNONYMOUS, "Inferred from same-residue ('=') HGVS protein notation."
    if _IN_FRAME_INDEL_RE.search(name):
        return ConsequenceType.IN_FRAME_INDEL, (
            "Inferred from del/dup/ins HGVS protein notation without 'fs' — "
            "reading frame preserved (indel length is a multiple of 3 nt)."
        )
    if _MISSENSE_RE.search(name):
        return ConsequenceType.MISSENSE, "Inferred from single amino-acid substitution HGVS protein notation."
    return None, (
        "Could not infer consequence type from HGVS notation — this proxy "
        "inference method has limited coverage; real deployment would use "
        "VEP or equivalent annotation instead."
    )


def load_clinvar_records(
    filepath: str | Path, gene_panel: set[str] | None = None
) -> list[ClinVarRecord]:
    """
    Parses a ClinVar-format TSV into ClinVarRecord objects.

    Args:
        filepath: path to a variant_summary.txt-style TSV.
        gene_panel: if provided, only records whose GeneSymbol is in this
            set are returned — mirrors the curated-panel filtering
            described in ADR 011 rather than loading all of ClinVar.

    Records with an unrecognized ReviewStatus value are skipped rather
    than guessed at.
    """
    filepath = Path(filepath)
    records: list[ClinVarRecord] = []

    with filepath.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            gene = row["GeneSymbol"].strip()
            if gene_panel is not None and gene not in gene_panel:
                continue

            review_status_raw = row["ReviewStatus"].strip()
            review_status = _REVIEW_STATUS_MAP.get(review_status_raw)
            if review_status is None:
                # Unrecognized review status string — skip rather than guess.
                continue

            consequence, note = _infer_consequence(row["Name"])
            phenotypes = [
                p.strip() for p in row["PhenotypeList"].split(";")
                if p.strip() and p.strip() != "not provided"
            ]

            records.append(
                ClinVarRecord(
                    gene=gene,
                    variant_name=row["Name"].strip(),
                    clinical_significance=row["ClinicalSignificance"].strip(),
                    review_status=review_status,
                    phenotypes=phenotypes,
                    inferred_consequence=consequence,
                    consequence_inference_note=note,
                )
            )

    return records