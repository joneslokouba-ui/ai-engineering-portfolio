# ADR 011: HELIX — Genetic Disorders Classification & Knowledge System

## Status
Accepted

## Context

Module 11 extends the AI engineering portfolio into genomics. Unlike prior
modules (fraud detection, critical minerals, drone systems), this domain
carries elevated stakes: outputs touch health information, and the biology
does not reduce to a single uniform model. Five distinct disorder categories
each have a different causal structure:

- **Monogenic** (e.g. Cystic Fibrosis/CFTR, Sickle Cell Disease/HBB,
  Huntington's Disease/HTT) — single-gene variant, maps to ClinVar
  pathogenicity classification.
- **Chromosomal** (e.g. Down Syndrome/trisomy 21, Turner Syndrome/45,X) —
  numerical or structural chromosome abnormality, not a variant call.
- **Multifactorial** (e.g. Type 2 Diabetes, Coronary Heart Disease) —
  polygenic contribution plus environmental factors; no single causal
  variant.
- **X-linked** (e.g. Duchenne Muscular Dystrophy/DMD, Hemophilia A/F8) —
  variant-level, but risk expression depends on sex-linked inheritance.
- **Mitochondrial** (e.g. MELAS, LHON/MT-ND4) — maternally inherited mtDNA
  variants, complicated by heteroplasmy (variant load varies by cell/tissue).

Treating all five with one classifier would misrepresent the underlying
biology. This ADR commits to five narrower, honest sub-models over one
inflated unified score.

## Decision

### 1. Governance boundary (stated up front, per portfolio convention)

HELIX explains and classifies **published, de-identified disorder and
variant knowledge**. It does not:
- diagnose, manage, or advise on any individual's care,
- accept or process any individual's personal genomic data,
- substitute for a clinical geneticist or genetic counselor.

All data is drawn from public reference databases (ClinVar, gnomAD, OMIM),
never from patient records.

### 2. Data ingestion — static, curated, offline-reproducible

Following the Bastion/AEGIS precedent of deterministic builds over live
external dependencies:

| Source | Method | Scope |
|---|---|---|
| ClinVar | Bulk `variant_summary.txt.gz` (NCBI FTP) | Filtered to curated gene panel |
| gnomAD | Static public summary extract | Population allele frequency, same gene panel |
| OMIM | Hand-curated gene→disorder/phenotype table | Same gene panel; structured into Causes/Inheritance, Prevalence, Research & Advances, Clinical Applications |

Curated gene panel (representative, ~15 genes across 5 categories) is fixed
at build time — no live API calls, no auth dependency, fully reproducible on
Streamlit Cloud.

### 3. Classification engine — five sub-models

| Category | Model approach | Output |
|---|---|---|
| Monogenic | ClinVar review-status + consequence-type + conservation score ensemble | Benign / VUS / Pathogenic tier |
| Chromosomal | Karyotype-pattern lookup (not variant-level) | Aneuploidy type + associated phenotype |
| Multifactorial | Simplified polygenic risk score (PRS) over curated risk-allele set | Relative risk tier (population-normalized) |
| X-linked | Monogenic-style scoring + sex-linked inheritance logic layer | Tier + carrier/affected inheritance note |
| Mitochondrial | Heteroplasmy-aware variant scoring (mtDNA reference) | Tier + heteroplasmy sensitivity note |

A routing layer inspects disorder category first, then dispatches to the
correct sub-model — this routing decision is itself the architecturally
interesting part of the module and will be documented in the Mermaid diagram.

### 4. Simulation layer

SimPy discrete-event simulation of a variant/case intake pipeline:
sample intake → category routing → sub-model classification → clinician
review queue. Tracks throughput and backlog by category, consistent with
Bastion/AEGIS simulation pattern.

### 5. Knowledge assistant — Hybrid RAG

Reuses the established α·VectorSim + (1−α)·KeywordScore hybrid formula
(Groq `llama-3.3-70b-versatile`) over the curated OMIM knowledge base,
structured to answer against the four fixed sections: Causes & Inheritance,
Prevalence, Research & Advances, Clinical Applications.

### 6. Dashboard

Streamlit app: disorder category browser, variant/case lookup with
sub-model-appropriate output display, pipeline throughput visualization,
RAG query interface with governance-boundary disclaimer surfaced
persistently in the UI (not just in this ADR).

### 7. Deployment

Streamlit Cloud, module-specific `requirements.txt` pointed to explicitly
in Advanced Settings, `sim/__init__.py` added preemptively, Sources Root
convention applied from first commit (avoiding the AEGIS-style retrofit).

## Consequences

**Positive:**
- Five honest sub-models are defensible under technical questioning in a
  way a single unified score would not be.
- Explicit governance boundary reduces risk of the module being
  (mis)represented as a diagnostic tool.
- Fully offline-reproducible — no demo-day dependency on external API
  availability.

**Trade-offs:**
- More build and validation surface than a single-model module (five
  category-specific scoring test suites required, not one).
- Curated gene panel means breadth is illustrative, not exhaustive —
  this is a design choice to state plainly in the README, not a hidden
  limitation.

## Next steps
1. Mermaid architecture diagram (routing layer + five sub-models + RAG + sim)
2. Curated gene panel finalization (5 genes × 5 categories)
3. Sub-model implementation, starting with Monogenic (most similar to
   AEGIS's existing ensemble pattern) as the reference implementation
4. Regression test suite per sub-model
5. Streamlit dashboard + deployment