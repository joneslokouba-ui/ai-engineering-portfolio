# ADR 012: Databricks lakehouse practice module

## Status
Accepted

## Context
Utility-sector AI teams commonly build on Databricks. The portfolio's existing modules
run on AWS (ECS/ECR, GitHub Actions) and Streamlit Cloud, with MLflow for tracking.
There was no hands-on Databricks work to show.

## Decision
Add a small learning module on Databricks Free Edition covering Delta tables, table
history, and MLflow tracking, plus a locally tested hybrid-scoring function reused from
the HybridRAG design.

## Consequences
- Honest scope: introductory exercises on a non-commercial free workspace, not production use.
- Scoring logic is unit-tested locally and independent of the platform.
- Notebook 03 (hybrid RAG on Databricks) is added only after it has been built and run.