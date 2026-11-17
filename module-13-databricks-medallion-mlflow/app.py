"""Module 13 - CER Pipeline Incidents: medallion pipeline and MLflow model.

Streamlit companion to the Databricks notebooks. The notebooks build bronze,
silver and gold Delta tables from the Canada Energy Regulator (CER) Pipeline
Incidents open dataset (Open Government Licence - Canada) and track a model in
MLflow. This app shows the pipeline design and reads small exports of the
results from the data/ folder:

- data/gold_*.csv         one CSV per gold table (export from notebook 04)
- data/model_metrics.json model comparison (export from notebook 05/06)

Until those files exist the app shows a clear placeholder instead of failing.
"""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).parent / "data"

st.set_page_config(page_title="CER Medallion Pipeline", layout="wide")

st.title("CER Pipeline Incidents: Medallion Pipeline and Model")
st.caption(
    "Module 13 - Databricks lakehouse. Data: Canada Energy Regulator, Pipeline Incidents "
    "(Open Government Licence - Canada). This app reads exported snapshots of the "
    "Databricks results."
)

tab_pipeline, tab_gold, tab_model = st.tabs(["Pipeline", "Gold tables", "Model results"])

with tab_pipeline:
    st.subheader("Medallion layers")
    st.markdown(
        """
| Layer | Table | Purpose |
|---|---|---|
| Bronze | `cer_bronze` | Raw CER CSV loaded as-is into a Delta table |
| Silver | `cer_silver` | Cleaned types, parsed dates, standardized names, duplicates removed |
| Data quality | `cer_dq_results` | Failed checks are written to a table so quality is visible |
| Gold | gold tables | Aggregates for analysis and the dashboard |
| Model | MLflow experiment | Baseline and gradient-boosted models predicting the `significant` flag |
"""
    )
    st.markdown(
        "Notebooks run in order: `01_bronze_ingest`, `02_silver_clean`, `03_data_quality`, "
        "`04_gold_aggregates`, `05_features_and_model`, `06_register_and_score`."
    )

with tab_gold:
    st.subheader("Gold tables")
    gold_files = sorted(DATA_DIR.glob("gold_*.csv"))
    if not gold_files:
        st.info(
            "No gold table exports yet. Export each gold table from notebook 04 and save it "
            "in the data/ folder with a name like gold_incidents_by_year_province.csv."
        )
    else:
        choice = st.selectbox("Table", [f.name for f in gold_files])
        table = pd.read_csv(DATA_DIR / choice)
        st.caption(f"{len(table):,} rows")
        st.dataframe(table, use_container_width=True, hide_index=True)

with tab_model:
    st.subheader("Model results")
    metrics_path = DATA_DIR / "model_metrics.json"
    if not metrics_path.exists():
        st.info(
            "No model results yet. Save the model comparison from the MLflow runs as "
            "data/model_metrics.json."
        )
    else:
        try:
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            st.dataframe(
                pd.DataFrame(metrics["models"]), use_container_width=True, hide_index=True
            )
            if metrics.get("notes"):
                st.caption(metrics["notes"])
        except (ValueError, KeyError) as exc:
            st.error(f"Could not read model_metrics.json: {exc}")
            st.caption('Expected format: {"models": [{"name": "...", "pr_auc": 0.0}], "notes": "..."}')

st.caption(
    "Limitations: the significant flag is rare, so precision, recall and PR-AUC are reported "
    "instead of accuracy; results come from a downloaded snapshot of the dataset."
)