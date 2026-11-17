# Databricks notebook source
# MAGIC %md
# MAGIC # 01 Bronze ingest
# MAGIC
# MAGIC Loads the raw Canada Energy Regulator (CER) Pipeline Incidents CSV into the bronze Delta
# MAGIC table `workspace.default.cer_bronze`.
# MAGIC
# MAGIC **Bronze rule:** values are kept exactly as they arrive (every column is read as text, nothing
# MAGIC is cleaned or dropped). Only the column *names* are normalized, because Delta does not allow
# MAGIC spaces or characters such as `(` and `)` in column names. Two metadata columns are added:
# MAGIC `_source_file` and `_ingested_at`.
# MAGIC
# MAGIC **Before running:** upload `pipeline-incidents-data.csv` to the volume
# MAGIC `/Volumes/workspace/default/raw/`.
# MAGIC
# MAGIC Source: Canada Energy Regulator, Pipeline Incidents (Open Government Licence - Canada).

# COMMAND ----------

CATALOG = "workspace"
SCHEMA = "default"
VOLUME = "raw"
FILE_NAME = "pipeline-incidents-data.csv"

SOURCE_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}/{FILE_NAME}"
BRONZE_TABLE = f"{CATALOG}.{SCHEMA}.cer_bronze"
EXPECTED_ROWS = 2034  # row count of the Nov 2, 2026 snapshot used in Module 12

print("Source:", SOURCE_PATH)
print("Target:", BRONZE_TABLE)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Check the uploaded file

# COMMAND ----------

display(dbutils.fs.ls(f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}/"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Read the CSV as text
# MAGIC
# MAGIC `multiLine` is on because some free-text columns (for example the incident descriptions)
# MAGIC can contain line breaks inside quoted values.

# COMMAND ----------

raw = (
    spark.read.format("csv")
    .option("header", True)
    .option("inferSchema", False)
    .option("multiLine", True)
    .option("quote", '"')
    .option("escape", '"')
    .option("encoding", "UTF-8")
    .load(SOURCE_PATH)
)

print("Rows read:", raw.count())
print("Columns read:", len(raw.columns))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Normalize column names
# MAGIC
# MAGIC Same rule as the Module 12 table: lowercase, every run of characters that is not a letter
# MAGIC or digit becomes one underscore. If two names collapse to the same text, a numeric suffix
# MAGIC is added so no column is lost. The same functions live in `src/naming.py` and are tested
# MAGIC with pytest.

# COMMAND ----------

import re


def normalize_name(name):
    cleaned = re.sub(r"[^0-9a-z]+", "_", str(name).strip().lower()).strip("_")
    return cleaned or "column"


def make_unique(names):
    seen = {}
    result = []
    for name in names:
        if name in seen:
            seen[name] += 1
            result.append(f"{name}_{seen[name]}")
        else:
            seen[name] = 1
            result.append(name)
    return result


new_names = make_unique([normalize_name(c) for c in raw.columns])
renamed = raw.toDF(*new_names)

changed = [(old, new) for old, new in zip(raw.columns, new_names) if old != new]
print(f"{len(changed)} of {len(new_names)} column names changed. First 10:")
for old, new in changed[:10]:
    print(f"  {old!r} -> {new!r}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Add metadata and write the bronze table

# COMMAND ----------

from pyspark.sql import functions as F

bronze = (
    renamed
    .withColumn("_source_file", F.lit(SOURCE_PATH))
    .withColumn("_ingested_at", F.current_timestamp())
)

(
    bronze.write.format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(BRONZE_TABLE)
)

print("Wrote", BRONZE_TABLE)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Verify

# COMMAND ----------

table = spark.table(BRONZE_TABLE)
row_count = table.count()

print("Rows in bronze:", row_count)
print("Columns in bronze (including 2 metadata columns):", len(table.columns))

assert row_count > 0, "Bronze table is empty"
if row_count != EXPECTED_ROWS:
    print(
        f"WARNING: expected {EXPECTED_ROWS} rows (Nov 2, 2026 snapshot) but found {row_count}. "
        "This is fine if you uploaded a newer snapshot; update EXPECTED_ROWS and the README."
    )
else:
    print("Row count matches the Module 12 snapshot.")

# COMMAND ----------

# Quick look at the data, and a text-encoding check: accented names should read correctly
# (for example "Quebec" or "Québec", not strange symbols). If you see garbled characters,
# change the encoding option in step 2 to "ISO-8859-1" and re-run.
display(table.groupBy("province").count().orderBy(F.desc("count")))

# COMMAND ----------

display(table.limit(10))