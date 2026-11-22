# Databricks notebook source
# MAGIC %md
# MAGIC # 03 Data quality
# MAGIC
# MAGIC Runs checks on `workspace.default.cer_silver` and appends the results to
# MAGIC `workspace.default.cer_dq_results`, so quality is visible over time and not hidden.
# MAGIC
# MAGIC - **error** checks protect the integrity of the data (missing or duplicate keys, negative
# MAGIC   volumes). If one fails, the notebook stops at the end so bad data does not flow on to gold.
# MAGIC - **warn** checks flag things worth knowing about (odd dates or coordinates, a missing model
# MAGIC   target) without stopping the pipeline.
# MAGIC
# MAGIC Source: Canada Energy Regulator, Pipeline Incidents (Open Government Licence - Canada).

# COMMAND ----------

from datetime import datetime, timezone

from pyspark.sql import functions as F

CATALOG = "workspace"
SCHEMA = "default"
BRONZE_TABLE = f"{CATALOG}.{SCHEMA}.cer_bronze"
SILVER_TABLE = f"{CATALOG}.{SCHEMA}.cer_silver"
DQ_TABLE = f"{CATALOG}.{SCHEMA}.cer_dq_results"

FAIL_ON_ERROR = True  # set to False to inspect failures without stopping the notebook

silver = spark.table(SILVER_TABLE)
bronze_rows = spark.table(BRONZE_TABLE).count()
total_rows = silver.count()
print("Bronze rows:", bronze_rows, "| Silver rows:", total_rows)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Row-level rules
# MAGIC
# MAGIC Each rule is a SQL condition that is true for a **bad** row. Rules only judge values that
# MAGIC are present, so a missing value is reported by its own "not null" rule, not by every rule.

# COMMAND ----------

RULES = [
    # (check name, severity, description, condition that is true for a bad row)
    ("incident_number_not_null", "error",
     "Every incident has an incident number",
     "incident_number IS NULL"),
    ("province_not_null", "error",
     "Every incident has a province or state",
     "province IS NULL"),
    ("volume_non_negative", "error",
     "Release volume is not negative",
     "volume_m3 < 0"),
    ("year_not_null", "warn",
     "Year is present",
     "year IS NULL"),
    ("year_in_range", "warn",
     "Year is between 2000 and the current year",
     "year IS NOT NULL AND (year < 2000 OR year > year(current_date()))"),
    ("reported_date_not_null", "warn",
     "Reported date was parsed",
     "reported_date IS NULL"),
    ("reported_date_not_future", "warn",
     "Reported date is not in the future",
     "reported_date > current_date()"),
    ("year_matches_reported_date", "warn",
     "Year column agrees with the reported date",
     "year IS NOT NULL AND reported_date IS NOT NULL AND year <> year(reported_date)"),
    ("closed_after_reported", "warn",
     "Closed date is not before the reported date",
     "closed_date IS NOT NULL AND reported_date IS NOT NULL AND closed_date < reported_date"),
    ("coordinates_in_range", "warn",
     "Coordinates fall roughly inside Canada and the border area",
     "(latitude IS NOT NULL AND (latitude < 40 OR latitude > 85)) "
     "OR (longitude IS NOT NULL AND (longitude < -145 OR longitude > -50))"),
    ("significant_flag_not_null", "warn",
     "Significant flag could be read as true or false (model target)",
     "significant_flag IS NULL"),
    ("company_encoding_ok", "warn",
     "Company names contain no replacement characters (text read with the wrong encoding)",
     "company LIKE '%" + "\ufffd" + "%'"),
]

aggs = [F.sum(F.when(F.expr(cond), 1).otherwise(0)).alias(name) for name, _, _, cond in RULES]
row_failures = silver.agg(*aggs).first().asDict()

results = []
for name, severity, description, _ in RULES:
    results.append((name, severity, description, int(row_failures[name] or 0)))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Table-level checks

# COMMAND ----------

non_null_keys = silver.filter(F.col("incident_number").isNotNull()).count()
distinct_keys = silver.select("incident_number").distinct().count()

results.append((
    "incident_number_unique", "error",
    "Incident numbers are unique",
    non_null_keys - distinct_keys,
))
results.append((
    "rows_lost_bronze_to_silver", "warn",
    "Rows removed between bronze and silver (duplicates or missing keys)",
    bronze_rows - total_rows,
))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Write the results

# COMMAND ----------

run_ts = datetime.now(timezone.utc).replace(tzinfo=None)

result_rows = [
    (run_ts, name, severity, description, int(total_rows), int(failed), failed == 0)
    for name, severity, description, failed in results
]
dq_df = spark.createDataFrame(
    result_rows,
    schema=(
        "run_ts timestamp, check_name string, severity string, description string, "
        "total_rows long, failed_rows long, passed boolean"
    ),
)

dq_df.write.format("delta").mode("append").saveAsTable(DQ_TABLE)
print("Appended", len(result_rows), "check results to", DQ_TABLE)

display(dq_df.orderBy(F.desc("failed_rows"), "check_name"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Examples of failing rows
# MAGIC
# MAGIC For every row-level check that found problems, show up to 5 example rows.

# COMMAND ----------

any_examples = False
for name, severity, description, _ in RULES:
    if row_failures[name] and row_failures[name] > 0:
        any_examples = True
        cond = next(c for n, _, _, c in RULES if n == name)
        print(f"[{severity}] {name}: {row_failures[name]} rows - {description}")
        display(
            silver.filter(F.expr(cond))
            .select("incident_number", "year", "reported_date", "province", "volume_m3",
                    "latitude", "longitude", "significant", "significant_flag")
            .limit(5)
        )
if not any_examples:
    print("No row-level failures to show.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Quality gate

# COMMAND ----------

failed_errors = [name for name, severity, _, failed in results if severity == "error" and failed > 0]
failed_warns = [name for name, severity, _, failed in results if severity == "warn" and failed > 0]

print("Error checks failed:", failed_errors or "none")
print("Warning checks with findings:", failed_warns or "none")

if failed_errors and FAIL_ON_ERROR:
    raise AssertionError(f"Data quality gate failed on: {failed_errors}")
print("Quality gate passed." if not failed_errors else "Gate bypassed (FAIL_ON_ERROR is False).")