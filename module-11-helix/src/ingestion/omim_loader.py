"""
Module 11 — HELIX: OMIM Loader
=================================
Parses the hand-curated gene->disorder->phenotype CSV into the same
four-section structure (Causes & Inheritance, Prevalence, Research &
Advances, Clinical Applications) used by the dashboard's knowledge base
stub (dashboard/app.py STUB_KNOWLEDGE_BASE) — this loader is what
eventually replaces that hardcoded dict with real curated data, and by
real_hybrid_rag.py's knowledge_base_builder.py once that's built.

Per ADR 011, OMIM's own API requires a registered key with usage
restrictions not worth the dependency risk on Streamlit Cloud — this
loader targets a hand-curated static CSV instead, built from OMIM's
public gene map for the curated panel only.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DisorderKnowledge:
    gene: str
    disorder: str
    causes_and_inheritance: str
    prevalence: str
    research_and_advances: str
    clinical_applications: str

    def as_sections(self) -> dict[str, str]:
        """Matches the section-keyed shape used by the dashboard's RAG stub."""
        return {
            "Causes & Inheritance": self.causes_and_inheritance,
            "Prevalence": self.prevalence,
            "Research & Advances": self.research_and_advances,
            "Clinical Applications": self.clinical_applications,
        }


_REQUIRED_COLUMNS = {
    "Gene", "Disorder", "CausesInheritance", "Prevalence",
    "ResearchAdvances", "ClinicalApplications",
}


def load_omim_knowledge(filepath: str | Path) -> dict[str, DisorderKnowledge]:
    """
    Parses the curated OMIM CSV into a {disorder_name: DisorderKnowledge}
    lookup, keyed by disorder name to match how the RAG assistant looks
    up entries by disorder in the dashboard.

    Raises ValueError if the file is missing any required column, or if
    any row has a blank value in a required field — an incomplete
    knowledge base entry should fail the build, not silently ship a gap.
    """
    filepath = Path(filepath)
    knowledge: dict[str, DisorderKnowledge] = {}

    with filepath.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing_columns = _REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing_columns:
            raise ValueError(
                f"OMIM CSV missing required columns: {sorted(missing_columns)}"
            )

        for row_num, row in enumerate(reader, start=2):
            for col in _REQUIRED_COLUMNS:
                if not row[col].strip():
                    raise ValueError(
                        f"OMIM CSV row {row_num}: column '{col}' is blank. "
                        f"Incomplete knowledge base entries are not allowed "
                        f"to ship silently."
                    )

            disorder = row["Disorder"].strip()
            knowledge[disorder] = DisorderKnowledge(
                gene=row["Gene"].strip(),
                disorder=disorder,
                causes_and_inheritance=row["CausesInheritance"].strip(),
                prevalence=row["Prevalence"].strip(),
                research_and_advances=row["ResearchAdvances"].strip(),
                clinical_applications=row["ClinicalApplications"].strip(),
            )

    return knowledge