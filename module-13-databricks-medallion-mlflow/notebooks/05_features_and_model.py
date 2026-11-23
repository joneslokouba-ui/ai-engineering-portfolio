# Databricks notebook source
# MAGIC %md
# MAGIC # 05 Features and model
# MAGIC
# MAGIC Trains models that predict the CER `significant` flag from `workspace.default.cer_silver` and
# MAGIC tracks every run in MLflow.
# MAGIC
# MAGIC **Question:** given what is known when an incident is first reported, can we flag the ones
# MAGIC that will be classed as significant?
# MAGIC
# MAGIC **Leakage policy.** Several columns are filled in after an incident is assessed or investigated,
# MAGIC and some of them effectively encode the answer. They are excluded on purpose:
# MAGIC - assessment and response fields: `investigation_type`, `emergency_level`, `was_neb_staff_deployed`, `status`, `closed_date`
# MAGIC - post-investigation findings: `what_happened_category`, `why_it_happened_category` and the detailed text columns
# MAGIC - outcomes: release volume, injuries, fatalities, evacuations
# MAGIC
# MAGIC **Two feature sets are compared:**
# MAGIC - `context_only`: where, who and what activity (province, company, facility type, activity, how it was discovered, land use, location, month)
# MAGIC - `reporting_time`: the same plus the reported incident type and the released substance
# MAGIC
# MAGIC The incident type is known at reporting, but it is close to the definition of "significant"
# MAGIC (for example serious injuries and fires), so the comparison shows how much of the signal it carries.
# MAGIC
# MAGIC **Split by time, not at random:** train 2008-2020, validation 2021-2022, test 2023-2026. Models are
# MAGIC chosen on validation PR-AUC; the test years are only reported. Accuracy is not used, because always
# MAGIC answering "no" is already about 82% accurate.
# MAGIC
# MAGIC Source: Canada Energy Regulator, Pipeline Incidents (Open Government Licence - Canada).

# COMMAND ----------

import json
import os
from datetime import datetime, timezone

import mlflow
import numpy as np
import pandas as pd
from mlflow.models import infer_signature
from pyspark.sql import functions as F
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score, f1_score, precision_score, recall_score, roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

CATALOG = "workspace"
SCHEMA = "default"
SILVER_TABLE = f"{CATALOG}.{SCHEMA}.cer_silver"
RESULTS_TABLE = f"{CATALOG}.{SCHEMA}.cer_model_results"
EXPORT_DIR = f"/Volumes/{CATALOG}/{SCHEMA}/raw/exports"

TARGET = "significant_flag"
TRAIN_END = 2020   # train: 2008-2020
VAL_END = 2022     # validation: 2021-2022, test: 2023 onwards
THRESHOLD = 0.5    # for precision, recall and F1 (PR-AUC and ROC-AUC do not use it)

CONTEXT_CATEGORICAL = [
    "province", "company_clean", "pipeline_or_facility_type",
    "activity_being_performed_at_time_of_incident", "how_the_incident_was_discovered",
    "land_use", "population_density", "affects_pipeline_right_of_way",
    "affects_company_property", "off_company_property",
]
REPORT_CATEGORICAL = ["incident_types", "release_substance"]
NUMERIC = ["latitude", "longitude", "reported_month"]
ALL_CATEGORICAL = sorted(set(CONTEXT_CATEGORICAL + REPORT_CATEGORICAL))

FEATURE_SETS = {
    "context_only": CONTEXT_CATEGORICAL,
    "reporting_time": CONTEXT_CATEGORICAL + REPORT_CATEGORICAL,
}
MODELS = ["baseline", "logistic_regression", "gradient_boosting"]

user = spark.sql("SELECT current_user()").first()[0]
EXPERIMENT = f"/Users/{user}/cer-significant-incidents"
BATCH_ID = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
print("Experiment:", EXPERIMENT, "| batch:", BATCH_ID)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Load silver and split by time

# COMMAND ----------

def load_frame(table, categorical, numeric):
    """Silver table to a pandas frame with the target, year and the model inputs."""
    sdf = (
        spark.table(table)
        .withColumn("reported_month", F.month("reported_date"))
        .select("incident_number", "year", TARGET, *numeric, *categorical)
    )
    pdf = sdf.toPandas()
    pdf[TARGET] = pdf[TARGET].astype(int)
    for c in categorical:
        pdf[c] = pdf[c].fillna("Missing").astype(str)
    for c in numeric:
        pdf[c] = pdf[c].astype(float)
    return pdf


df = load_frame(SILVER_TABLE, ALL_CATEGORICAL, NUMERIC)
assert TARGET not in ALL_CATEGORICAL + NUMERIC, "The target must never be a feature"

train = df[df["year"] <= TRAIN_END]
val = df[(df["year"] > TRAIN_END) & (df["year"] <= VAL_END)]
test = df[df["year"] > VAL_END]

for name, part in [("train", train), ("validation", val), ("test", test)]:
    print(f"{name:10s} rows={len(part):5d}  years={part['year'].min()}-{part['year'].max()}  "
          f"significant rate={part[TARGET].mean():.3f}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Model helpers

# COMMAND ----------

# --- BEGIN MODEL HELPERS ---
def make_model(name):
    if name == "baseline":
        return DummyClassifier(strategy="prior")  # predicts the training-set rate for everyone
    if name == "logistic_regression":
        return LogisticRegression(C=1.0, class_weight="balanced", max_iter=2000)
    if name == "gradient_boosting":
        return GradientBoostingClassifier(
            n_estimators=200, learning_rate=0.05, max_depth=3, subsample=0.8, random_state=42
        )
    raise ValueError(name)


def model_params(name):
    if name == "logistic_regression":
        return {"C": 1.0, "class_weight": "balanced", "max_iter": 2000}
    if name == "gradient_boosting":
        return {"n_estimators": 200, "learning_rate": 0.05, "max_depth": 3, "subsample": 0.8}
    return {}


def make_pipeline(model_name, categorical, numeric):
    prep = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=10), categorical),
        ("num", Pipeline([("impute", SimpleImputer(strategy="median")),
                          ("scale", StandardScaler())]), numeric),
    ])
    return Pipeline([("prep", prep), ("model", make_model(model_name))])


def evaluate(pipe, X, y, prefix):
    proba = pipe.predict_proba(X)[:, 1]
    pred = (proba >= THRESHOLD).astype(int)
    return {
        f"{prefix}_precision": float(precision_score(y, pred, zero_division=0)),
        f"{prefix}_recall": float(recall_score(y, pred, zero_division=0)),
        f"{prefix}_f1": float(f1_score(y, pred, zero_division=0)),
        f"{prefix}_pr_auc": float(average_precision_score(y, proba)),
        f"{prefix}_roc_auc": float(roc_auc_score(y, proba)),
        f"{prefix}_prevalence": float(np.mean(y)),
    }


def top_features(pipe, n=15):
    """Indicative feature weights (importances for trees, absolute coefficients for logistic)."""
    est = pipe.named_steps["model"]
    if hasattr(est, "feature_importances_"):
        scores = est.feature_importances_
    elif hasattr(est, "coef_"):
        scores = np.abs(est.coef_[0])
    else:
        return None
    names = pipe.named_steps["prep"].get_feature_names_out()
    order = np.argsort(scores)[::-1][:n]
    return [{"feature": str(names[i]), "score": round(float(scores[i]), 4)} for i in order]
# --- END MODEL HELPERS ---

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Train and track every run in MLflow
# MAGIC
# MAGIC Each run logs its parameters, validation and test metrics, the feature list, indicative feature
# MAGIC weights and the fitted pipeline (with a signature and an input example).

# COMMAND ----------

mlflow.set_experiment(EXPERIMENT)
results = []

for feature_set, categorical in FEATURE_SETS.items():
    feature_cols = categorical + NUMERIC
    for model_name in MODELS:
        pipe = make_pipeline(model_name, categorical, NUMERIC)
        pipe.fit(train[feature_cols], train[TARGET])

        metrics = {}
        metrics.update(evaluate(pipe, val[feature_cols], val[TARGET], "val"))
        metrics.update(evaluate(pipe, test[feature_cols], test[TARGET], "test"))
        metrics["train_prevalence"] = float(train[TARGET].mean())

        with mlflow.start_run(run_name=f"{feature_set}__{model_name}") as run:
            mlflow.set_tags({
                "project": "cer-significant", "batch_id": BATCH_ID,
                "feature_set": feature_set, "model_type": model_name,
            })
            mlflow.log_params({
                "feature_set": feature_set, "model_type": model_name,
                "train_years": f"2008-{TRAIN_END}", "val_years": f"{TRAIN_END + 1}-{VAL_END}",
                "test_years": f"{VAL_END + 1}-{int(df['year'].max())}",
                "train_end": TRAIN_END, "val_end": VAL_END, "threshold": THRESHOLD,
                "n_train": len(train), "n_val": len(val), "n_test": len(test),
                **model_params(model_name),
            })
            mlflow.log_metrics(metrics)
            mlflow.log_dict(
                {"features": feature_cols, "categorical": categorical, "numeric": NUMERIC},
                "features.json",
            )
            weights = top_features(pipe)
            if weights:
                mlflow.log_dict({"top_features": weights}, "top_features.json")

            signature = infer_signature(train[feature_cols], pipe.predict(train[feature_cols]))
            # cloudpickle avoids the skops "untrusted types" error that newer MLflow versions raise
            # for scikit-learn pipelines that contain numpy dtypes
            info = mlflow.sklearn.log_model(
                pipe, artifact_path="model", signature=signature,
                input_example=train[feature_cols].head(3),
                serialization_format="cloudpickle",
            )
            mlflow.set_tag("model_uri", info.model_uri)

            results.append({
                "batch_id": BATCH_ID, "run_id": run.info.run_id,
                "feature_set": feature_set, "model": model_name,
                **{k: round(v, 4) for k, v in metrics.items()},
            })
        print(f"{feature_set:15s} {model_name:20s} val PR-AUC={metrics['val_pr_auc']:.3f}  "
              f"test PR-AUC={metrics['test_pr_auc']:.3f}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Compare the runs
# MAGIC
# MAGIC A model only counts if it beats the baseline. The baseline's PR-AUC equals the share of
# MAGIC significant incidents (the prevalence), so that is the number to beat.

# COMMAND ----------

results_df = pd.DataFrame(results).sort_values("val_pr_auc", ascending=False).reset_index(drop=True)
display(spark.createDataFrame(results_df))

(
    spark.createDataFrame(results_df)
    .write.format("delta").mode("overwrite").option("overwriteSchema", "true")
    .saveAsTable(RESULTS_TABLE)
)
print("Wrote", RESULTS_TABLE)

# COMMAND ----------

for feature_set in FEATURE_SETS:
    part = results_df[results_df["feature_set"] == feature_set]
    base = part[part["model"] == "baseline"].iloc[0]
    best = part[part["model"] != "baseline"].sort_values("val_pr_auc", ascending=False).iloc[0]
    print(f"[{feature_set}] best model on validation: {best['model']}")
    print(f"   validation PR-AUC {best['val_pr_auc']:.3f} vs baseline {base['val_pr_auc']:.3f}")
    print(f"   test PR-AUC       {best['test_pr_auc']:.3f} vs baseline {base['test_pr_auc']:.3f}")
    print(f"   test precision {best['test_precision']:.3f}, recall {best['test_recall']:.3f}, F1 {best['test_f1']:.3f}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Export a compact results file for the Streamlit app

# COMMAND ----------

summary = results_df[[
    "feature_set", "model", "val_pr_auc", "test_pr_auc", "test_precision", "test_recall", "test_f1",
]].to_dict(orient="records")

notes = (
    f"Time split: train 2008-{TRAIN_END} (n={len(train)}), validation {TRAIN_END + 1}-{VAL_END} "
    f"(n={len(val)}), test {VAL_END + 1}-{int(df['year'].max())} (n={len(test)}). "
    f"Share of significant incidents: train {train[TARGET].mean():.1%}, validation {val[TARGET].mean():.1%}, "
    f"test {test[TARGET].mean():.1%}. Models are chosen on validation PR-AUC; precision, recall and F1 use a "
    f"{THRESHOLD} threshold. The baseline predicts the training rate for every incident, so its PR-AUC equals "
    f"the share of significant incidents in each period."
)

os.makedirs(EXPORT_DIR, exist_ok=True)
with open(f"{EXPORT_DIR}/model_metrics.json", "w", encoding="utf-8") as f:
    json.dump({"models": summary, "notes": notes}, f, indent=2)
print("Wrote", f"{EXPORT_DIR}/model_metrics.json")
print(notes)