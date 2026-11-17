# Module 12: Databricks lakehouse practice

A learning module built on **Databricks Free Edition**. It documents introductory work
with the lakehouse model, not a production deployment.

## Module 12: Databricks (Free Edition), introductory

Hands-on introduction to Databricks Free Edition, built as five notebooks
(`01`–`05`) covering [fill in from notebooks 01–04].

**Notebook 05: real CSV through a Volume.** Downloaded the public CER
Pipeline Incidents CSV, uploaded it to a Unity Catalog Volume, read it with
Spark, cleaned the column names and saved it as a Delta table
(`workspace.default.cer_pipeline_incidents`) with basic quality checks.

**Dataset:** Canada Energy Regulator, Pipeline Incidents, published under the
Open Government Licence – Canada
(https://www.cer-rec.gc.ca/open/incident/pipeline-incidents-data.csv).
2,034 incidents, 2008–2026 (2026 is a partial year).

**Data checks before analysis**
- No duplicate incident numbers; `year` agrees with `reported_date`.
- Release volume is stored as text. Only 594 incidents have a numeric volume
  ("Not Applicable" or "Not Provided" for the rest), so volume statistics
  use `TRY_CAST` and cover that subset only.
- Medians are reported per substance, only where 5+ incidents report a
  volume (561 incidents). Volumes aren't comparable across substances.

**Dashboard:** counter, stacked incidents per year by province with a
province filter, and a median-release table, built in a Databricks
dashboard. Started from the auto-generated dashboard, then curated.

**Scope and limits:** a learning project on a small public dataset in a free
workspace. It is not a production pipeline.

![Incidents per year by province](screenshots/dashboard-incidents.png)

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

## Streamlit app

`app.py` is a portable view of the same analysis as the Databricks dashboard, so it can be opened without a Databricks login.

- **Data:** Canada Energy Regulator, Pipeline Incidents (CSV), published under the Open Government Licence - Canada. The app reads a downloaded snapshot stored at `data/pipeline-incidents-data.csv` (snapshot date: YYYY-MM-DD).
- **Views:** total incidents, incidents per year by province (with a province filter), and median release volume by substance for substances with 5+ incidents.
- **Data note:** the release volume column is text in the source and only some incidents have a numeric value, so medians use those incidents only.
- **Relationship to Databricks:** the Databricks dashboard runs live in the workspace on `workspace.default.cer_pipeline_incidents`; the Streamlit app reads the same public file as a static snapshot.

**Run locally**

```
pip install -r requirements.txt
streamlit run app.py
```

Live app: <add Streamlit Cloud URL after deployment>