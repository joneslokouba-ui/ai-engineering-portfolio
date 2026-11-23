# Databricks notebook source
# MAGIC %md
# MAGIC # 06 Register and score
# MAGIC
# MAGIC Takes the best model from notebook 05, registers it in the Unity Catalog model registry, loads
# MAGIC it back by its `champion` alias, and scores the incidents.
# MAGIC
# MAGIC - **Champion:** the non-baseline run from the latest notebook 05 batch with the highest
# MAGIC   **validation** PR-AUC. The test years are never used to choose.
# MAGIC - **Scoring table:** `workspace.default.cer_scored_incidents`, with a `split` column so it is always
# MAGIC   clear which rows the model was trained on. Only the `test` rows (2023 onwards) say anything about
# MAGIC   how the model might do on new incidents.
# MAGIC - **Reading the result:** the question is not "what is the accuracy" but "if we review the
# MAGIC   incidents the model ranks highest, how many are really significant, compared with picking at random?"
# MAGIC
# MAGIC Source: Canada Energy Regulator, Pipeline Incidents (Open Government Licence - Canada).

# COMMAND ----------

import json

import mlflow
import numpy as np
import pandas as pd
from mlflow.tracking import MlflowClient
from pyspark.sql import functions as F

CATALOG = "workspace"
SCHEMA = "default"
SILVER_TABLE = f"{CATALOG}.{SCHEMA}.cer_silver"
SCORED_TABLE = f"{CATALOG}.{SCHEMA}.cer_scored_incidents"
MODEL_NAME = f"{CATALOG}.{SCHEMA}.cer_significant_incident_model"
TARGET = "significant_flag"

user = spark.sql("SELECT current_user()").first()[0]
EXPERIMENT = f"/Users/{user}/cer-significant-incidents"

mlflow.set_registry_uri("databricks-uc")
print("Experiment:", EXPERIMENT)
print("Model name:", MODEL_NAME)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Pick the champion from the latest batch

# COMMAND ----------

all_runs = mlflow.search_runs(
    experiment_names=[EXPERIMENT],
    filter_string="tags.project = 'cer-significant'",
    max_results=500,
)
latest_batch = all_runs["tags.batch_id"].max()
batch_runs = all_runs[all_runs["tags.batch_id"] == latest_batch]
candidates = (
    batch_runs[batch_runs["tags.model_type"] != "baseline"]
    .sort_values("metrics.val_pr_auc", ascending=False)
)

print("Latest batch:", latest_batch, "| runs:", len(batch_runs))
display(spark.createDataFrame(candidates[[
    "run_id", "tags.feature_set", "tags.model_type", "metrics.val_pr_auc", "metrics.test_pr_auc",
    "metrics.test_precision", "metrics.test_recall", "metrics.test_f1",
]].rename(columns=lambda c: c.replace("tags.", "").replace("metrics.", "").replace(".", "_"))))

champion = candidates.iloc[0]
run_id = champion["run_id"]
print(f"\nChampion: {champion['tags.feature_set']} / {champion['tags.model_type']} (run {run_id})")
print(f"  validation PR-AUC {champion['metrics.val_pr_auc']:.3f}, test PR-AUC {champion['metrics.test_pr_auc']:.3f}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Register it in Unity Catalog and set the `champion` alias

# COMMAND ----------

model_uri = champion["tags.model_uri"]
registered = mlflow.register_model(model_uri, MODEL_NAME)

client = MlflowClient()
client.set_registered_model_alias(MODEL_NAME, "champion", registered.version)
print(f"Registered {MODEL_NAME} version {registered.version} with alias 'champion'")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Load it back by alias and score every incident

# COMMAND ----------

model = mlflow.sklearn.load_model(f"models:/{MODEL_NAME}@champion")

features_path = mlflow.artifacts.download_artifacts(run_id=run_id, artifact_path="features.json")
with open(features_path, encoding="utf-8") as f:
    features = json.load(f)
feature_cols = features["features"]
train_end = int(float(champion["params.train_end"]))
val_end = int(float(champion["params.val_end"]))


def load_frame(table, categorical, numeric):
    """Same preparation as notebook 05 (keep the two in sync)."""
    # The three display columns are kept even when the model does not use them
    display_cols = ["incident_types", "company_clean", "release_substance"]
    cols = list(dict.fromkeys(["incident_number", "year", TARGET] + numeric + categorical + display_cols))
    sdf = spark.table(table).withColumn("reported_month", F.month("reported_date")).select(*cols)
    pdf = sdf.toPandas()
    pdf[TARGET] = pdf[TARGET].astype(int)
    for c in dict.fromkeys(categorical + display_cols):
        pdf[c] = pdf[c].fillna("Missing").astype(str)
    for c in numeric:
        pdf[c] = pdf[c].astype(float)
    return pdf


scored = load_frame(SILVER_TABLE, features["categorical"], features["numeric"])
scored["split"] = np.where(
    scored["year"] <= train_end, "train", np.where(scored["year"] <= val_end, "validation", "test")
)
scored["predicted_probability"] = model.predict_proba(scored[feature_cols])[:, 1]
scored["predicted_flag"] = (scored["predicted_probability"] >= 0.5).astype(int)

out_cols = ["incident_number", "year", "split", TARGET, "predicted_probability", "predicted_flag"]
(
    spark.createDataFrame(scored[out_cols])
    .write.format("delta").mode("overwrite").option("overwriteSchema", "true")
    .saveAsTable(SCORED_TABLE)
)
print("Wrote", SCORED_TABLE, "| rows:", len(scored))
print(scored.groupby("split").size().to_string())

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. How useful is the ranking on the held-out years?
# MAGIC
# MAGIC If we review only the incidents the model ranks highest, how many are really significant?
# MAGIC Lift compares that with picking incidents at random (the overall share of significant incidents).

# COMMAND ----------

test_df = scored[scored["split"] == "test"].sort_values("predicted_probability", ascending=False)
base_rate = test_df[TARGET].mean()
print(f"Test incidents: {len(test_df)} | share significant (random pick): {base_rate:.1%}\n")

for k in (25, 50, 100):
    top = test_df.head(k)
    precision_k = top[TARGET].mean()
    print(f"Top {k:3d} by predicted probability: {int(top[TARGET].sum()):3d} significant "
          f"= {precision_k:.1%}  (lift {precision_k / base_rate:.2f}x)")

# COMMAND ----------

display(spark.createDataFrame(
    test_df.head(15)[["incident_number", "year", "incident_types", "company_clean", "release_substance",
                      "predicted_probability", TARGET]]
))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. What the model leans on
# MAGIC
# MAGIC Indicative feature weights saved with the champion run (importances for trees, absolute
# MAGIC coefficients for logistic regression). They show what the model uses, not what causes an
# MAGIC incident to be significant.

# COMMAND ----------

try:
    weights_path = mlflow.artifacts.download_artifacts(run_id=run_id, artifact_path="top_features.json")
    with open(weights_path, encoding="utf-8") as f:
        display(spark.createDataFrame(pd.DataFrame(json.load(f)["top_features"])))
except Exception as exc:  # the baseline has no weights; other runs should
    print("No feature weights saved for this run:", exc)