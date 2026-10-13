# Databricks notebook source
# MAGIC %md
# MAGIC # 04 Large data practice
# MAGIC Practice handling a few million rows on Databricks Free Edition, without uploading anything.
# MAGIC Spark generates **synthetic** pipeline sensor readings, writes them to a partitioned Delta table,
# MAGIC and summarizes them per pipeline segment.
# MAGIC
# MAGIC **Scope notes**
# MAGIC - The data is synthetic (random numbers with a slow wall-thickness decline), not real readings.
# MAGIC - Free Edition has compute quotas, so keep `N_ROWS` modest. If the workspace hits its quota, compute pauses
# MAGIC   until the limit resets, and your tables are kept.
# MAGIC - Other ways to bring in large data are listed in the last cell.

# COMMAND ----------

# Cell 1: size settings (start small, raise only if everything runs quickly)
N_ROWS = 2_000_000
N_SEGMENTS = 50
N_DAYS = 30

# COMMAND ----------

# Cell 2: generate synthetic readings in parallel with Spark
from pyspark.sql import functions as F

readings = (
    spark.range(N_ROWS)
    .withColumn("segment_id", F.concat(F.lit("seg_"), F.lpad((F.col("id") % N_SEGMENTS).cast("string"), 2, "0")))
    .withColumn("day_index", (F.col("id") % N_DAYS).cast("int"))
    .withColumn("day", F.date_add(F.lit("2026-01-01").cast("date"), F.col("day_index")))
    .withColumn("pressure_kpa", F.lit(5000.0) + F.randn(7) * 100)
    .withColumn("flow_m3h", F.lit(800.0) + F.randn(11) * 40)
    .withColumn("wall_mm", F.lit(10.0) - F.col("day_index") * 0.002 + F.randn(13) * 0.05)
    .withColumn("flow_dip", F.rand(17) < 0.001)
    .withColumn("flow_m3h", F.when(F.col("flow_dip"), F.col("flow_m3h") * 0.85).otherwise(F.col("flow_m3h")))
    .withColumnRenamed("id", "reading_id")
)
print(f"Columns: {readings.columns}")

# COMMAND ----------

# Cell 3: write a Delta table partitioned by day
(
    readings.write.format("delta")
    .mode("overwrite")
    .partitionBy("day")
    .saveAsTable("pipeline_readings_demo")
)
print(spark.table("pipeline_readings_demo").count(), "rows written")

# COMMAND ----------

# Cell 4: inspect the table's physical layout (number of files, size on storage)
display(spark.sql("DESCRIBE DETAIL pipeline_readings_demo").select("numFiles", "sizeInBytes", "partitionColumns"))

# COMMAND ----------

# Cell 5: per-segment summary, timed
import time

start = time.time()
summary = (
    spark.table("pipeline_readings_demo")
    .groupBy("segment_id")
    .agg(
        F.round(F.avg("pressure_kpa"), 1).alias("avg_pressure_kpa"),
        F.round(F.min("wall_mm"), 3).alias("min_wall_mm"),
        F.sum(F.col("flow_dip").cast("int")).alias("flow_dip_count"),
    )
    .orderBy("min_wall_mm")
)
display(summary.limit(10))
print(f"Summary took {time.time() - start:.1f} seconds")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Other ways to bring in large data
# MAGIC 1. **Built-in sample tables:** open **Catalog** and check for a `samples` catalog. Read tables with `spark.table("samples.<schema>.<table>")`.
# MAGIC 2. **Upload a file to a Unity Catalog Volume** (best for larger files): Catalog, then your catalog and schema,
# MAGIC    then create a Volume and upload. Read it with
# MAGIC    `spark.read.csv("/Volumes/workspace/default/<volume>/<file>.csv", header=True, inferSchema=True)`.
# MAGIC 3. **Code downloads are limited:** Free Edition restricts outbound internet to a small set of trusted domains,
# MAGIC    so download files to your computer first, then upload them.