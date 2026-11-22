# Databricks notebook source
# MAGIC %md
# MAGIC # 02 Silver clean
# MAGIC
# MAGIC Reads `workspace.default.cer_bronze` (all text) and writes `workspace.default.cer_silver`
# MAGIC with proper types and a few standardized helper columns.
# MAGIC
# MAGIC **What silver does**
# MAGIC - trims whitespace and turns empty strings and the text "null" into nulls
# MAGIC - converts dates, timestamps, numbers and counts to real types (unparseable values become
# MAGIC   null and are **counted in a parse report**, never silently dropped)
# MAGIC - adds helper columns: `volume_m3`, `significant_flag`, `is_canadian_province`,
# MAGIC   `release_substance`, `company_clean`
# MAGIC - removes duplicate incident numbers and reports how many there were
# MAGIC
# MAGIC Source: Canada Energy Regulator, Pipeline Incidents (Open Government Licence - Canada).

# COMMAND ----------

from pyspark.sql import functions as F

CATALOG = "workspace"
SCHEMA = "default"
BRONZE_TABLE = f"{CATALOG}.{SCHEMA}.cer_bronze"
SILVER_TABLE = f"{CATALOG}.{SCHEMA}.cer_silver"
META_COLS = ["_source_file", "_ingested_at"]
EXPECTED_ROWS = 2034          # Module 12 snapshot
EXPECTED_NUMERIC_VOLUMES = 594  # Module 12: incidents with a numeric release volume

bronze = spark.table(BRONZE_TABLE)
print("Bronze rows:", bronze.count(), "| columns:", len(bronze.columns))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Trim text and turn empty strings and the text "null" into nulls

# COMMAND ----------

data_cols = [c for c in bronze.columns if c not in META_COLS]

trimmed = bronze.select(
    *[
        F.when(F.lower(F.trim(F.col(c))).isin("", "null"), None).otherwise(F.trim(F.col(c))).alias(c)
        for c in data_cols
    ],
    *[F.col(c) for c in META_COLS],
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Typing rules
# MAGIC
# MAGIC Databricks serverless runs with ANSI mode on, so a plain cast of bad text raises an error.
# MAGIC `try_cast` and `try_to_timestamp` return null instead, which lets us count the failures.

# COMMAND ----------

DATE_FORMATS = ["M/d/yyyy", "yyyy-MM-dd"]
TS_FORMATS = [
    "yyyy/MM/dd hh:mm:ss a",
    "yyyy/MM/dd HH:mm:ss",
    "M/d/yyyy H:mm",
    "M/d/yyyy H:mm:ss",
    "M/d/yyyy h:mm a",
    "M/d/yyyy h:mm:ss a",
    "yyyy-MM-dd HH:mm:ss",
    "M/d/yyyy",
    "yyyy-MM-dd",
]

# column -> (target type, formats)
TYPE_RULES = {
    "reported_date": ("date", DATE_FORMATS),
    "occurrence_date_and_time": ("timestamp", TS_FORMATS),
    "discovered_date_and_time": ("timestamp", TS_FORMATS),
    "closed_date": ("date", DATE_FORMATS),
    "year": ("int", None),
    "latitude": ("double", None),
    "longitude": ("double", None),
    "number_of_fatalities": ("int", None),
    "number_of_individuals_injured": ("int", None),
    "number_of_people_evacuated": ("int", None),
    "workdays_lost": ("int", None),
}
TYPE_RULES = {c: rule for c, rule in TYPE_RULES.items() if c in trimmed.columns}


def parse_ts(col_name, formats):
    # Timestamps in the CER file look like "2017/02/21 05:00:00 PM Mountain": a local time
    # followed by a time-zone name. The zone name is split into its own column further down;
    # here everything after AM or PM is removed before parsing.
    text = f"regexp_replace(`{col_name}`, '(?<=[AP]M) +.*$', '')"
    return F.coalesce(*[F.expr(f"try_to_timestamp({text}, '{fmt}')") for fmt in formats])


def typed_expr(col_name, kind, formats):
    number = f"try_cast(regexp_replace(`{col_name}`, ',', '') AS DOUBLE)"
    if kind == "date":
        return parse_ts(col_name, formats).cast("date")
    if kind == "timestamp":
        return parse_ts(col_name, formats)
    if kind == "int":
        return F.expr(f"CAST({number} AS INT)")
    if kind == "double":
        return F.expr(number)
    raise ValueError(f"Unknown type: {kind}")


print("Columns being typed:", list(TYPE_RULES))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Parse report
# MAGIC
# MAGIC For every typed column: how many values were present, how many parsed, and how many failed.
# MAGIC A large `failed` number means the format list above needs another pattern.

# COMMAND ----------

agg_exprs = []
for c, (kind, formats) in TYPE_RULES.items():
    agg_exprs.append(F.count(F.col(c)).alias(f"{c}__raw"))
    agg_exprs.append(F.count(typed_expr(c, kind, formats)).alias(f"{c}__parsed"))

counts = trimmed.agg(*agg_exprs).first().asDict()
report_rows = [
    (
        c,
        kind,
        int(counts[f"{c}__raw"]),
        int(counts[f"{c}__parsed"]),
        int(counts[f"{c}__raw"] - counts[f"{c}__parsed"]),
    )
    for c, (kind, _) in TYPE_RULES.items()
]
parse_report = spark.createDataFrame(
    report_rows, schema="column string, type string, raw_non_null long, parsed long, failed long"
)
display(parse_report.orderBy(F.desc("failed")))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Look at the category values before we encode them
# MAGIC
# MAGIC The `significant` flag is the target for the model in notebooks 05-06, so we check
# MAGIC exactly what values it holds instead of guessing.

# COMMAND ----------

display(trimmed.groupBy("significant").count().orderBy(F.desc("count")))

# COMMAND ----------

display(trimmed.groupBy("substance").count().orderBy(F.desc("count")).limit(15))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Apply the typing rules and add helper columns

# COMMAND ----------

CANADIAN_PROVINCES = [
    "Alberta", "British Columbia", "Manitoba", "New Brunswick",
    "Newfoundland and Labrador", "Northwest Territories", "Nova Scotia", "Nunavut",
    "Ontario", "Prince Edward Island", "Quebec", "Saskatchewan", "Yukon",
]

silver_df = (
    trimmed
    # Time-zone name after the time ("Mountain", "Pacific", ...), kept as its own column
    .withColumn("occurrence_timezone",
                F.expr("nullif(regexp_extract(`occurrence_date_and_time`, '(?<=[AP]M) +(.*)$', 1), '')"))
    .withColumn("discovered_timezone",
                F.expr("nullif(regexp_extract(`discovered_date_and_time`, '(?<=[AP]M) +(.*)$', 1), '')"))
)
for c, (kind, formats) in TYPE_RULES.items():
    silver_df = silver_df.withColumn(c, typed_expr(c, kind, formats))

# Same legal entity written differently. Explicit and reviewable (mirrors src/company.py);
# distinct legal entities are deliberately NOT merged.
COMPANY_ALIASES = {
    "NGTL GP Ltd., as general partner, on behalf of NGTL Limited Partnership":
        "NGTL GP Ltd., as general partner on behalf of NGTL Limited Partnership",
    "Westcoast Energy Inc., carrying on business as Spectra Energy Transmission":
        "Westcoast Energy Inc.",
    "Alliance Pipeline Ltd., as General Partner for and on behalf of Alliance Pipeline Limited Partnership":
        "Alliance Pipeline Ltd.",
    "Minell Pipeline Limited":
        "Minell Pipeline Ltd.",
    "TransCanada PipeLines Limited B.C. System":
        "TransCanada PipeLines Limited",
}
company_map = F.create_map([F.lit(x) for pair in COMPANY_ALIASES.items() for x in pair])

significant_text = F.lower(F.col("significant"))

silver_df = (
    silver_df
    # Release volume as a number (same source column as the Module 12 dashboard)
    .withColumn(
        "volume_m3",
        F.expr("try_cast(regexp_replace(`approximate_volume_released_m3`, ',', '') AS DOUBLE)"),
    )
    # Model target: yes/no text to boolean; anything else stays null so we can see it
    .withColumn(
        "significant_flag",
        F.when(significant_text.isin("yes", "true", "y", "1"), True)
        .when(significant_text.isin("no", "false", "n", "0"), False),
    )
    # The province column also holds one US state (Maine) for cross-border pipelines
    .withColumn("is_canadian_province", F.col("province").isin(CANADIAN_PROVINCES))
    # Standardized company name; the original company column is kept unchanged
    .withColumn("company_clean", F.coalesce(company_map[F.col("company")], F.col("company")))
    # "Not Applicable" means nothing was released; keep the original column, add a clean one
    .withColumn(
        "release_substance",
        F.when(F.lower(F.col("substance")) == "not applicable", None).otherwise(F.col("substance")),
    )
    .withColumn("_silver_processed_at", F.current_timestamp())
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Duplicates
# MAGIC
# MAGIC `incident_number` should be unique. We report what we find, then keep one row per number.

# COMMAND ----------

total_rows = silver_df.count()
null_keys = silver_df.filter(F.col("incident_number").isNull()).count()
distinct_keys = silver_df.select("incident_number").distinct().count()

print("Rows:", total_rows)
print("Rows with no incident_number:", null_keys)
print("Distinct incident numbers:", distinct_keys)
print("Duplicate rows by incident_number:", total_rows - null_keys - distinct_keys)

silver = silver_df.filter(F.col("incident_number").isNotNull()).dropDuplicates(["incident_number"])

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Write the silver table

# COMMAND ----------

(
    silver.write.format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(SILVER_TABLE)
)
print("Wrote", SILVER_TABLE)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Verify

# COMMAND ----------

check = spark.table(SILVER_TABLE)
rows = check.count()
numeric_volumes = check.filter(F.col("volume_m3").isNotNull()).count()

print("Silver rows:", rows)
print("Silver columns:", len(check.columns))
print("Incidents with a numeric volume:", numeric_volumes)
print("Distinct company names:", check.select("company").distinct().count(),
      "->", check.select("company_clean").distinct().count(), "after cleaning (expected: 5 fewer)")
print("Occurrence timestamps parsed:",
      check.filter(F.col("occurrence_date_and_time").isNotNull()).count(), "of", rows)

assert rows > 0, "Silver table is empty"
print("Row count matches Module 12." if rows == EXPECTED_ROWS
      else f"NOTE: expected {EXPECTED_ROWS} rows but found {rows}; check the duplicate report above.")
print("Numeric volume count matches Module 12." if numeric_volumes == EXPECTED_NUMERIC_VOLUMES
      else f"NOTE: expected {EXPECTED_NUMERIC_VOLUMES} numeric volumes but found {numeric_volumes}.")

typed_cols = list(TYPE_RULES) + ["volume_m3", "significant_flag", "is_canadian_province", "release_substance"]
for name, dtype in check.select(*typed_cols).dtypes:
    print(f"  {name}: {dtype}")

# COMMAND ----------

# Incidents per year should match the Module 12 dashboard (for example 2012 and 2017 are the tallest bars)
display(check.groupBy("year").count().orderBy("year"))

# COMMAND ----------

display(check.groupBy("significant_flag").count())

# COMMAND ----------

display(
    check.select(
        "incident_number", "reported_date", "year", "province", "is_canadian_province",
        "substance", "release_substance", "volume_m3", "significant", "significant_flag",
    ).limit(15)
)