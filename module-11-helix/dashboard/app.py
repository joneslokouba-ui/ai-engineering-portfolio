"""
Module 11 — HELIX: Streamlit Dashboard
========================================
Entry point: `streamlit run app.py`

Per the incremental-verification pattern established in ADR 011, this
dashboard is wired against the STUB simulation/classification layer
(sim/intake_pipeline_sim.py) so the pipeline is demoable end-to-end before
the five real sub-models (models/monogenic_model.py, etc.) and the real
ingestion layer (ingestion/clinvar_loader.py, etc.) are implemented.

Wherever this dashboard is using stub logic instead of a real component,
it says so explicitly in the UI — nothing here should read as more
finished than it is.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# module-11-helix/ (this file's grandparent) must be on sys.path so
# `src.*` and `sim.*` resolve as packages — dashboard/ itself is a
# sibling of src/ and sim/, not their parent, so appending only this
# file's own directory (as an earlier version of this file did) left
# every downstream import unresolved, both in PyCharm and on Streamlit
# Cloud (where the working directory is the repo root, not dashboard/).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sim.intake_pipeline_sim import Category, CATEGORY_WEIGHTS, run_simulation

from src.routing.category_router import (
    ChromosomalCase,
    MitochondrialCase,
    MonogenicCase,
    MultifactorialCase,
    XLinkedCase,
    route_case,
)
from src.models.monogenic_model import ConsequenceType, ReviewStatus, VariantFeatures
from src.models.multifactorial_model import AlleleDosage, EnvironmentalFactor, PolygenicProfile, RiskAllele
from src.models.xlinked_model import XLinkedFeatures, Zygosity


# ---------------------------------------------------------------------------
# Governance boundary text — surfaced persistently, not just once
# ---------------------------------------------------------------------------

GOVERNANCE_NOTICE = (
    "**HELIX explains and classifies published, de-identified genetic "
    "research data.** It does not diagnose, manage, or advise on any "
    "individual's care, and does not accept personal genomic data. "
    "All data shown is drawn from public reference sources (ClinVar, "
    "gnomAD, OMIM) or, where noted, from stub placeholder logic pending "
    "full implementation."
)

# ---------------------------------------------------------------------------
# Curated gene panel (stub — mirrors the eventual data/processed/
# curated_gene_panel.csv, hardcoded here until ingestion/*.py is built)
# ---------------------------------------------------------------------------

GENE_PANEL = [
    {"gene": "CFTR", "disorder": "Cystic Fibrosis", "category": Category.MONOGENIC},
    {"gene": "HBB", "disorder": "Sickle Cell Disease", "category": Category.MONOGENIC},
    {"gene": "HTT", "disorder": "Huntington's Disease", "category": Category.MONOGENIC},
    {"gene": "Trisomy 21", "disorder": "Down Syndrome", "category": Category.CHROMOSOMAL},
    {"gene": "45,X", "disorder": "Turner Syndrome", "category": Category.CHROMOSOMAL},
    {"gene": "Polygenic (multi-locus)", "disorder": "Type 2 Diabetes", "category": Category.MULTIFACTORIAL},
    {"gene": "Polygenic (multi-locus)", "disorder": "Coronary Heart Disease", "category": Category.MULTIFACTORIAL},
    {"gene": "DMD", "disorder": "Duchenne Muscular Dystrophy", "category": Category.XLINKED},
    {"gene": "F8", "disorder": "Hemophilia A", "category": Category.XLINKED},
    {"gene": "MT-TL1", "disorder": "MELAS", "category": Category.MITOCHONDRIAL},
    {"gene": "MT-ND4", "disorder": "Leber Hereditary Optic Neuropathy", "category": Category.MITOCHONDRIAL},
]

# ---------------------------------------------------------------------------
# Stub knowledge base — mirrors the eventual OMIM-derived RAG corpus.
# Structured against the four fixed sections from ADR 011. Real build will
# replace this dict with knowledge_base_builder.py output + hybrid_rag.py
# retrieval over Groq llama-3.3-70b-versatile.
# ---------------------------------------------------------------------------

STUB_KNOWLEDGE_BASE = {
    "Cystic Fibrosis": {
        "Causes & Inheritance": "Autosomal recessive; caused by mutations in the CFTR gene affecting chloride ion transport.",
        "Prevalence": "Approximately 1 in 2,500–3,500 live births in populations of European descent.",
        "Research & Advances": "CFTR modulator therapies (e.g. elexacaftor/tezacaftor/ivacaftor combinations) target the underlying protein defect rather than only symptoms.",
        "Clinical Applications": "Diagnosis via newborn screening and sweat chloride test; management includes airway clearance and CFTR modulators; genetic carrier screening supports family planning.",
    },
    "Sickle Cell Disease": {
        "Causes & Inheritance": "Autosomal recessive; single point mutation in the HBB gene producing abnormal hemoglobin S.",
        "Prevalence": "Most common in populations with historical malaria exposure; carrier rates exceed 10% in parts of sub-Saharan Africa.",
        "Research & Advances": "Gene therapy approaches (e.g. CRISPR-based reactivation of fetal hemoglobin) have reached clinical use in recent years.",
        "Clinical Applications": "Diagnosis via newborn screening and hemoglobin electrophoresis; management includes hydroxyurea therapy and pain crisis management.",
    },
    "Huntington's Disease": {
        "Causes & Inheritance": "Autosomal dominant; CAG trinucleotide repeat expansion in the HTT gene.",
        "Prevalence": "Roughly 3–7 per 100,000 in populations of Western European descent.",
        "Research & Advances": "Antisense oligonucleotide and gene-silencing approaches targeting mutant HTT are in active clinical trials.",
        "Clinical Applications": "Predictive genetic testing available for at-risk individuals; management is symptomatic, focused on movement and psychiatric symptoms.",
    },
    "Down Syndrome": {
        "Causes & Inheritance": "Chromosomal — trisomy of chromosome 21, usually arising from meiotic nondisjunction.",
        "Prevalence": "Approximately 1 in 700 live births; risk increases with maternal age.",
        "Research & Advances": "Research focuses on cognitive and cardiac outcome interventions rather than gene-level correction.",
        "Clinical Applications": "Diagnosis via prenatal screening/karyotype; management is multidisciplinary, addressing cardiac, developmental, and endocrine needs.",
    },
    "Turner Syndrome": {
        "Causes & Inheritance": "Chromosomal — complete or partial absence of one X chromosome in females.",
        "Prevalence": "Approximately 1 in 2,000–2,500 live female births.",
        "Research & Advances": "Growth hormone and estrogen replacement protocols continue to be refined for long-term outcomes.",
        "Clinical Applications": "Diagnosis via karyotype; management includes growth hormone therapy, cardiac monitoring, and hormone replacement.",
    },
    "Type 2 Diabetes": {
        "Causes & Inheritance": "Multifactorial — polygenic risk combined with lifestyle and environmental factors.",
        "Prevalence": "Affects roughly 1 in 10 adults globally, with substantial regional variation.",
        "Research & Advances": "Polygenic risk scores are increasingly studied as an early-identification tool alongside traditional clinical risk factors.",
        "Clinical Applications": "Diagnosis via blood glucose/HbA1c testing; prevention emphasizes lifestyle intervention informed by genetic and clinical risk.",
    },
    "Coronary Heart Disease": {
        "Causes & Inheritance": "Multifactorial — polygenic contribution combined with cardiovascular risk factors.",
        "Prevalence": "Leading cause of death globally; prevalence rises sharply with age.",
        "Research & Advances": "Genome-wide association studies continue to expand the set of risk loci used in polygenic risk scoring.",
        "Clinical Applications": "Prevention centers on modifiable risk factors; polygenic risk scores are an emerging adjunct to traditional risk calculators.",
    },
    "Duchenne Muscular Dystrophy": {
        "Causes & Inheritance": "X-linked recessive; mutations in the DMD gene disrupting dystrophin protein production.",
        "Prevalence": "Approximately 1 in 3,500–5,000 male births.",
        "Research & Advances": "Exon-skipping antisense therapies and micro-dystrophin gene therapy have advanced to clinical use.",
        "Clinical Applications": "Diagnosis via genetic testing and elevated creatine kinase; management includes corticosteroids and emerging gene-targeted therapies.",
    },
    "Hemophilia A": {
        "Causes & Inheritance": "X-linked recessive; mutations in the F8 gene reducing clotting factor VIII activity.",
        "Prevalence": "Approximately 1 in 5,000 male births.",
        "Research & Advances": "Adeno-associated virus (AAV) gene therapy delivering functional F8 has reached approved clinical use in recent years.",
        "Clinical Applications": "Diagnosis via factor VIII assay; management includes factor replacement and, increasingly, gene therapy.",
    },
    "MELAS": {
        "Causes & Inheritance": "Mitochondrial — maternally inherited mtDNA mutations, most commonly in MT-TL1; severity depends on heteroplasmy level.",
        "Prevalence": "Estimated at roughly 1 in 4,000, though under-diagnosis is likely given variable presentation.",
        "Research & Advances": "Research is exploring mitochondrial replacement techniques and metabolic cofactor therapies.",
        "Clinical Applications": "Diagnosis via mtDNA sequencing and muscle biopsy; management is largely supportive, addressing stroke-like episodes and metabolic crises.",
    },
    "Leber Hereditary Optic Neuropathy": {
        "Causes & Inheritance": "Mitochondrial — maternally inherited mtDNA mutations, commonly in MT-ND4; heteroplasmy affects penetrance.",
        "Prevalence": "Estimated at roughly 1 in 30,000–50,000, with higher penetrance in males.",
        "Research & Advances": "Gene therapy delivering functional ND4 via intravitreal injection has been studied in clinical trials.",
        "Clinical Applications": "Diagnosis via mtDNA testing following vision loss presentation; management is largely supportive, with gene therapy emerging.",
    },
}


def stub_rag_query(question: str) -> str:
    """
    Keyword-overlap retrieval stub standing in for hybrid_rag.py's
    alpha*VectorSim + (1-alpha)*KeywordScore formula against Groq
    llama-3.3-70b-versatile. Matches the question to the disorder with the
    most keyword overlap and returns its structured knowledge base entry.
    """
    question_lower = question.lower()
    best_match, best_score = None, 0
    for disorder in STUB_KNOWLEDGE_BASE:
        score = sum(1 for word in disorder.lower().split() if word in question_lower)
        if score > best_score:
            best_match, best_score = disorder, score

    if not best_match:
        return (
            "No confident match found in the stub knowledge base for that "
            "query. (Real build: hybrid_rag.py will retrieve over the full "
            "OMIM-derived corpus rather than this ~11-disorder stub set.)"
        )

    sections = STUB_KNOWLEDGE_BASE[best_match]
    lines = [f"**{best_match}**\n"]
    for section, text in sections.items():
        lines.append(f"**{section}:** {text}")
    return "\n\n".join(lines)


# ---------------------------------------------------------------------------
# Streamlit page
# ---------------------------------------------------------------------------

st.set_page_config(page_title="HELIX — Genetic Disorders Classification", layout="wide")

st.title("HELIX — Genetic Disorders Classification & Knowledge System")
st.caption("Module 11 · AI Engineering Portfolio")

st.info(GOVERNANCE_NOTICE)

tab_browser, tab_lookup, tab_pipeline, tab_rag = st.tabs(
    ["Category Browser", "Case Lookup", "Pipeline Metrics", "RAG Assistant"]
)

# --- Tab 1: Category Browser -------------------------------------------

with tab_browser:
    st.subheader("Disorder Categories")
    st.caption(
        "Five categories, each routed to a distinct sub-model per ADR 011 — "
        "the biology does not reduce to one uniform classifier."
    )
    df_panel = pd.DataFrame(
        [{"Gene/Locus": g["gene"], "Disorder": g["disorder"], "Category": g["category"].value}
         for g in GENE_PANEL]
    )
    for category in Category:
        with st.expander(f"{category.value}  ({(df_panel['Category'] == category.value).sum()} disorders in panel)"):
            st.dataframe(
                df_panel[df_panel["Category"] == category.value].reset_index(drop=True),
                use_container_width=True,
            )

# --- Tab 2: Case Lookup --------------------------------------------------

with tab_lookup:
    st.subheader("Case / Variant Lookup")
    st.success(
        "Classification below runs through the REAL category router and "
        "sub-models (category_router.py -> models/*.py) — not a stub. "
        "Input values are still manually entered here since the ingestion "
        "layer (ClinVar/gnomAD/OMIM loaders) is not yet built.",
        icon="✅",
    )

    category_choice = st.selectbox("Select a disorder category:", [c.value for c in Category])
    selected_category = Category(category_choice)

    if selected_category in (Category.MONOGENIC, Category.XLINKED):
        gene_options = ["CFTR", "HBB", "HTT"] if selected_category == Category.MONOGENIC else ["DMD", "F8"]
        gene = st.selectbox("Gene", gene_options)
        consequence = st.selectbox("Consequence type", [c.value for c in ConsequenceType])
        review_status = st.selectbox("ClinVar review status", [r.value for r in ReviewStatus])
        conservation = st.slider("Conservation score", 0.0, 1.0, 0.5)
        af = st.number_input("gnomAD allele frequency", min_value=0.0, max_value=1.0, value=0.001, format="%.6f")

        zygosity = None
        if selected_category == Category.XLINKED:
            zygosity = st.selectbox("Zygosity", [z.value for z in Zygosity])

        if st.button("Run classification"):
            features = VariantFeatures(
                gene=gene,
                consequence=ConsequenceType(consequence),
                review_status=ReviewStatus(review_status),
                conservation_score=conservation,
                gnomad_allele_frequency=af,
            )
            if selected_category == Category.MONOGENIC:
                result = route_case(MonogenicCase(features=features))
            else:
                result = route_case(
                    XLinkedCase(features=XLinkedFeatures(variant=features, zygosity=Zygosity(zygosity)))
                )
            st.markdown(f"**Result:** {result.summary_label}")
            st.caption("Matched" if result.matched else "No confident call")
            with st.expander("Rationale"):
                for line in result.rationale:
                    st.write(f"- {line}")

    elif selected_category == Category.CHROMOSOMAL:
        karyotype = st.text_input("Karyotype (ISCN-style)", value="47,XX,+21")
        st.caption("Examples: 46,XX · 45,X · 47,XX,+21 · 47,XX,+21[80]/46,XX[20]")
        if st.button("Run classification"):
            result = route_case(ChromosomalCase(karyotype=karyotype))
            st.markdown(f"**Result:** {result.summary_label}")
            st.caption("Matched" if result.matched else "No confident call")
            with st.expander("Rationale"):
                for line in result.rationale:
                    st.write(f"- {line}")

    elif selected_category == Category.MULTIFACTORIAL:
        disorder = st.selectbox("Disorder", ["Type 2 Diabetes", "Coronary Heart Disease"])
        num_alleles = st.slider("Number of risk alleles in profile", 2, 8, 4)
        env_factors = st.multiselect("Environmental risk factors", [f.value for f in EnvironmentalFactor])

        if st.button("Run classification"):
            rng = random.Random()
            dosages = []
            for i in range(num_alleles):
                allele = RiskAllele(
                    rsid=f"rs{rng.randint(1000, 9999)}",
                    effect_weight=rng.uniform(0.1, 0.6),
                    population_allele_frequency=rng.uniform(0.05, 0.5),
                )
                dosages.append(AlleleDosage(allele=allele, dosage=rng.choice([0, 1, 2])))
            profile = PolygenicProfile(
                disorder=disorder,
                dosages=dosages,
                environmental_factors=[EnvironmentalFactor(f) for f in env_factors],
            )
            result = route_case(MultifactorialCase(profile=profile))
            st.markdown(f"**Result:** {result.summary_label}")
            st.caption(
                f"Risk alleles randomly generated for this demo run "
                f"(no ingestion layer yet) — {num_alleles} alleles used."
            )
            with st.expander("Rationale"):
                for line in result.rationale:
                    st.write(f"- {line}")

    elif selected_category == Category.MITOCHONDRIAL:
        variant_id = st.selectbox("mtDNA variant", ["m.3243A>G", "m.11778G>A", "m.9999X>Y (unrecognized)"])
        variant_id = variant_id.split(" ")[0]
        heteroplasmy = st.slider("Heteroplasmy (%)", 0.0, 100.0, 50.0)

        if st.button("Run classification"):
            result = route_case(MitochondrialCase(variant_id=variant_id, heteroplasmy_pct=heteroplasmy))
            st.markdown(f"**Result:** {result.summary_label}")
            st.caption("Matched" if result.matched else "No confident call")
            with st.expander("Rationale"):
                for line in result.rationale:
                    st.write(f"- {line}")

# --- Tab 3: Pipeline Metrics ----------------------------------------------

with tab_pipeline:
    st.subheader("Intake Pipeline Throughput")
    st.caption(
        "SimPy discrete-event simulation: sample intake → category router → "
        "sub-model (stub) → clinician review queue."
    )

    col_a, col_b, col_c = st.columns(3)
    num_cases = col_a.slider("Cases to simulate", 50, 500, 200, step=50)
    mean_interarrival = col_b.slider("Mean interarrival (min)", 1.0, 10.0, 3.0, step=0.5)
    num_reviewers = col_c.slider("Clinician reviewers", 1, 6, 2)

    if st.button("Run simulation"):
        metrics = run_simulation(
            num_cases=num_cases,
            mean_interarrival=mean_interarrival,
            num_clinician_reviewers=num_reviewers,
        )
        rows = []
        for r in metrics.records:
            rows.append({
                "Category": r.category.value,
                "Tier": r.tier,
                "Classification (min)": round(r.classification_time, 2),
                "Review Wait (min)": round(r.review_wait, 2),
                "Total Time (min)": round(r.total_time_in_system, 2),
            })
        df = pd.DataFrame(rows)

        completed = len(df)
        st.metric("Cases completed", f"{completed}/{num_cases}")
        if completed < num_cases:
            st.warning(
                "Review queue under-provisioned relative to arrival rate — "
                "backlog signal, not a bug. Try increasing reviewer count."
            )

        st.bar_chart(df.groupby("Category")["Total Time (min)"].mean())
        st.dataframe(df, use_container_width=True)

# --- Tab 4: RAG Assistant --------------------------------------------------

with tab_rag:
    st.subheader("Knowledge Assistant")
    st.warning(
        "This assistant currently runs on a **stub keyword-match retriever** "
        "over an 11-disorder placeholder knowledge base — not the real "
        "hybrid_rag.py (α·VectorSim + (1−α)·KeywordScore over Groq "
        "llama-3.3-70b-versatile) described in ADR 011.",
        icon="⚠️",
    )
    st.caption(GOVERNANCE_NOTICE)

    query = st.text_input(
        "Ask about a disorder in the curated panel:",
        placeholder="e.g. What is the inheritance pattern for Cystic Fibrosis?",
    )
    if query:
        st.markdown(stub_rag_query(query))