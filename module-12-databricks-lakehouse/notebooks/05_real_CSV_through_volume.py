# Databricks notebook source
# MAGIC %md
# MAGIC # 05 Real CSV through a Volume
# MAGIC Bring a real public file into Databricks Free Edition: upload it to a Unity Catalog Volume, read it with Spark,
# MAGIC clean the column names, and save it as a Delta table with basic quality checks.
# MAGIC
# MAGIC **Dataset:** Canada Energy Regulator, *Pipeline Incidents* (CSV), published under the Open Government Licence - Canada.
# MAGIC Download it to your computer first (Free Edition cannot fetch files from most websites by code):
# MAGIC `https://www.cer-rec.gc.ca/open/incident/pipeline-incidents-data.csv`
# MAGIC
# MAGIC **Before running:** create a Volume (Catalog, then your catalog and schema, then Create, then Volume) and upload the CSV into it.

# COMMAND ----------

# Cell 1: where the file lives. Edit these three names to match what Catalog shows.
CATALOG = "workspace"
SCHEMA = "default"
VOLUME = "raw_files"
FILE_NAME = "pipeline-incidents-data.csv"

folder = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}"
path = f"{folder}/{FILE_NAME}"
display(dbutils.fs.ls(folder))

# COMMAND ----------

# Cell 2: read the CSV. If accented characters look garbled, add .option("encoding", "ISO-8859-1").
raw = (
    spark.read.option("header", True)
    .option("inferSchema", True)
    .option("multiLine", True)
    .option("escape", '"')
    .csv(path)
)
print("Rows:", raw.count(), "| Columns:", len(raw.columns))
raw.printSchema()
display(raw.limit(10))

# COMMAND ----------

# Cell 3: real files have messy column names; Delta rejects spaces and some symbols, so standardize them
import re


def clean(name: str) -> str:
    return re.sub(r"[^0-9a-zA-Z]+", "_", name).strip("_").lower()


seen, new_cols = {}, []
for c in raw.columns:
    base = clean(c) or "col"
    seen[base] = seen.get(base, 0) + 1
    new_cols.append(base if seen[base] == 1 else f"{base}_{seen[base]}")

df = raw.toDF(*new_cols)
df.write.format("delta").mode("overwrite").saveAsTable("cer_pipeline_incidents")
print("Saved table cer_pipeline_incidents with columns:")
print(new_cols)

# COMMAND ----------

# Cell 4: basic quality checks that work on any table
from pyspark.sql import functions as F

table = spark.table("cer_pipeline_incidents")
total = table.count()
print("Total rows:", total)
print("Duplicate rows:", total - table.dropDuplicates().count())

null_counts = table.select(
    [F.sum(F.col(c).isNull().cast("int")).alias(c) for c in table.columns]
).first().asDict()
nulls = sorted(((c, n) for c, n in null_counts.items()), key=lambda item: item[1], reverse=True)
display(spark.createDataFrame([(c, int(n), round(100 * n / total, 1)) for c, n in nulls], ["column", "null_count", "null_pct"]))

# COMMAND ----------

# Cell 5: check text encoding (a company name in this file contains an accented letter)
display(table.filter(F.col("company").contains("Pouce")).select("company").distinct())
# If you see a replacement symbol instead of an accented letter, add .option("encoding", "ISO-8859-1")
# to the read in cell 2, then re-run cells 2 to 5.

# COMMAND ----------

# Cell 6: first real summaries. Column names are the cleaned versions of the file's headers.
table = spark.table("cer_pipeline_incidents")

# Incidents per year
display(table.groupBy("year").count().orderBy("year"))

# Incidents per province
display(table.groupBy("province").count().orderBy(F.desc("count")))

# "What happened category" can hold several comma-separated labels, so split and count each label
labels = (
    table.select(F.explode(F.split(F.col("what_happened_category"), r",\s*")).alias("what_happened"))
    .where(F.col("what_happened").isNotNull() & (F.col("what_happened") != ""))
    .groupBy("what_happened")
    .count()
    .orderBy(F.desc("count"))
)
display(labels)

# COMMAND ----------

# Cell 7: released volume. The column mixes numbers with text such as "Not Applicable", so convert safely.
volumes = table.withColumn("volume_m3", F.expr("try_cast(approximate_volume_released_m3 as double)"))
print("Rows with a numeric released volume:", volumes.where(F.col("volume_m3").isNotNull()).count())
display(
    volumes.where(F.col("volume_m3").isNotNull())
    .groupBy("substance")
    .agg(F.count("*").alias("incidents"), F.round(F.sum("volume_m3"), 1).alias("total_m3"))
    .orderBy(F.desc("total_m3"))
    .limit(10)
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Notes
# MAGIC - The file has about 100 columns, and many are empty for most rows (for example wall thickness and operating pressure),
# MAGIC   which the null-percentage table in cell 4 shows.
# MAGIC - Some columns mix numbers and text, and some hold several values in one field, so cleaning matters more than the query.
# MAGIC - The data dictionary CSV explains each column. Keep the licence note (Open Government Licence - Canada) and the source URL in the README.