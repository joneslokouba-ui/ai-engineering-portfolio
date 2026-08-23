# Module 11 — HELIX: Genetic Disorders Classification & Knowledge System

Part of the [AI Engineering Portfolio](../). Classifies and explains genetic
disorder data across five biologically distinct categories, each routed to
its own purpose-built sub-model rather than forced into one uniform
classifier. See [ADR 011](../docs/adr/011-helix-genetic-disorders-classification-system.md)
for the full architecture decision record.

## Governance boundary

**HELIX explains and classifies published, de-identified genetic research
data. It does not diagnose, manage, or advise on any individual's care, and
does not accept or process personal genomic data.** This boundary is
code-enforced (`src/governance/authority_boundary.py`), not just stated —
every classification result and RAG response is checked for language that
crosses from population/reference-level explanation into individually
directed medical advice before being surfaced.

## Architecture

Five disorder categories, five distinct modeling approaches — because the
underlying biology genuinely doesn't reduce to one classifier:

| Category | Approach | Example disorders |
|---|---|---|
| Monogenic | ClinVar review-status + consequence-type + conservation ensemble | Cystic Fibrosis, Sickle Cell Disease, Huntington's Disease |
| Chromosomal | Karyotype-pattern lookup (with mosaicism handling) | Down Syndrome, Turner Syndrome |
| Multifactorial | Population-normalized polygenic risk score (PRS) | Type 2 Diabetes, Coronary Heart Disease |
| X-linked | Monogenic engine + sex-linked inheritance/zygosity layer | Duchenne Muscular Dystrophy, Hemophilia A |
| Mitochondrial | Heteroplasmy-threshold-aware mtDNA variant lookup | MELAS, Leber Hereditary Optic Neuropathy |

A category router (`src/routing/category_router.py`) dispatches each case
to its sub-model and normalizes the five heterogeneous result types into
one common shape for the dashboard and simulation to consume.

See [`diagrams/helix_architecture.mmd`](diagrams/helix_architecture.mmd)
for the full data flow diagram.

## Data sources

Static, curated, offline-reproducible — no live external dependency:

- **ClinVar** — bulk `variant_summary.txt`-style extract, filtered to a
  curated ~15-gene panel (see `data/processed/curated_gene_panel.csv`)
- **gnomAD** — static population allele frequency extract for the same panel
- **OMIM** — hand-curated gene→disorder→phenotype table, structured against
  four fixed sections (Causes & Inheritance, Prevalence, Research &
  Advances, Clinical Applications)

Real downloads for `data/raw/` are pulled outside this repo's build
process; `tests/fixtures/` contains small representative samples used for
automated testing.

## Knowledge assistant (Hybrid RAG)

`src/rag/` implements the portfolio's established hybrid retrieval formula:

```
score = alpha * VectorSim(query, chunk) + (1 - alpha) * KeywordScore(query, chunk)
```

**Design note:** VectorSim uses TF-IDF vectors (scikit-learn + FAISS)
rather than neural embeddings. Pulling pretrained embedding weights from
an external model hub would be a live dependency this module deliberately
avoids everywhere else — this keeps retrieval fully offline and
deterministic. Only the final answer-generation step calls out, to Groq.

**Model note (Aug 2026):** generation runs on `openai/gpt-oss-120b`.
The portfolio's original standard, `llama-3.3-70b-versatile`, was
decommissioned by Groq on August 16, 2026 — this module was migrated at
that time; other modules using the old model string (e.g. Bastion) are
still pending the same update.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

Create a `.env` file (never committed — see `.gitignore`) with:
```
GROQ_API_KEY=your_key_here
```

Run the test suite:
```bash
pytest tests/ -v
```

Run the dashboard locally:
```bash
streamlit run dashboard/app.py
```

## Known limitations (stated explicitly, not hidden)

- **Curated panel, not full coverage.** ~15 genes across 5 categories,
  chosen for representativeness and interview-defensibility, not
  exhaustive clinical coverage.
- **Consequence inference from HGVS notation is a simplified proxy**
  (`src/ingestion/clinvar_loader.py`) standing in for real VEP/SnpEql
  annotation — documented in-code, not silently assumed accurate.
- **No conservation score source** is wired in yet (would be phyloP/GERP
  in a real deployment); the ingestion layer requires it be supplied
  explicitly rather than fabricating a value.
- **Skewed X-inactivation** is flagged as a possibility for heterozygous
  X-linked carriers but not modeled quantitatively.
- **TF-IDF, not neural embeddings**, powers retrieval (see RAG section
  above) — a deliberate offline-reproducibility trade-off.
- **Multifactorial risk scores are relative population percentiles**,
  never individual predictions — this is the category where overclaiming
  is easiest, so the framing is enforced in the rationale text itself.

## Test coverage

97+ tests across ingestion, all five sub-models, the router, the
governance boundary, and RAG retrieval — including regression tests for
two real bugs caught during development (a ClinVar/gnomAD variant-name
join mismatch, and a missing in-frame-indel classification for CFTR's
ΔF508, the most common cystic fibrosis-causing variant).

```bash
pytest tests/ -v
```