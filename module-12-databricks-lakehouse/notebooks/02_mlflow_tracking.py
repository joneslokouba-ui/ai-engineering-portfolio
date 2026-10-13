# Databricks notebook source
# MAGIC %md
# MAGIC # 02 MLflow tracking
# MAGIC Log a run to see where experiments appear in the workspace.
# MAGIC The metric below is a placeholder value for learning the UI, not a real result.

# COMMAND ----------

import mlflow

with mlflow.start_run(run_name="alpha_demo"):
    mlflow.log_param("alpha", 0.6)
    mlflow.log_metric("demo_score", 0.5)