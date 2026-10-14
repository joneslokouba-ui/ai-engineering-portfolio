# Module 12: Databricks lakehouse practice

A learning module built on **Databricks Free Edition**. It documents introductory work
with the lakehouse model, not a production deployment.

## What is covered
- **Delta tables:** create, update, inspect history, query an earlier version (`notebooks/01_delta_basics.py`)
- **MLflow tracking:** log parameters and metrics from a notebook (`notebooks/02_mlflow_tracking.py`)
- **Hybrid scoring:** `alpha x VectorSim + (1 - alpha) x KeywordScore` as a tested, reusable function (`src/hybrid_score.py`)
- Notebook 03: TF-IDF hybrid retrieval over synthetic documents, with MLflow tracking per alpha
- Notebook 05: public Canada Energy Regulator pipeline-incidents CSV (about 2,000 rows, 102 columns) loaded through a Unity Catalog Volume, with column cleaning, a text-encoding fix, quality checks, and summaries. Source and licence: Open Government Licence - Canada. Add the source URL.
## Run the tests locally
```bash
pip install -r requirements.txt
pytest
```

## Run the notebooks
Import the `.py` files from `notebooks/` into a Databricks Free Edition workspace and run them on serverless compute.

## Documentation
- Decision record: `docs/adr/012-databricks-lakehouse-practice.md`
- Data flow diagram (Mermaid): `docs/architecture.mmd`
