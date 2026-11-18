# Databricks notebook source
# MAGIC %md
# MAGIC # 04 Gold aggregates
# MAGIC
# MAGIC Builds the gold tables from `workspace.default.cer_silver`. Each gold table answers one
# MAGIC question and is small enough to power a dashboard directly:
# MAGIC
# MAGIC | Table | Question |
# MAGIC |---|---|
# MAGIC | `gold_kpis` | How big is the dataset? (single row of headline numbers) |
# MAGIC | `gold_incidents_by_year_province` | How many incidents per year in each province? |
# MAGIC | `gold_release_by_substance` | How much is released, by substance? |
# MAGIC | `gold_incident_types_by_year` | What kinds of incidents happen, and when? |
# MAGIC | `gold_causes` | What happened, and why? |
# MAGIC | `gold_top_companies` | Which companies report the most incidents? |
# MAGIC | `gold_significant_by_year` | How often are incidents classed as significant? |
# MAGIC | `gold_incident_locations` | Where did incidents happen? (for a map) |
# MAGIC
# MAGIC Source: Canada Energy Regulator, Pipeline Incidents (Open Government Licence - Canada).

# COMMAND ----------

from pyspark.sql import functions as F

CATALOG = "workspace"
SCHEMA = "default"
SILVER_TABLE = f"{CATALOG}.{SCHEMA}.cer_silver"

silver = spark.table(SILVER_TABLE)
print("Silver rows:", silver.count())

GOLD_NAMES = []


def save_gold(df, name):
    table = f"{CATALOG}.{SCHEMA}.gold_{name}"
    (
        df.write.format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(table)
    )
    GOLD_NAMES.append(name)
    print(f"{table}: {spark.table(table).count()} rows")
    return spark.table(table)


# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Headline numbers

# COMMAND ----------

kpis = silver.agg(
    F.count("*").alias("total_incidents"),
    F.sum(F.when(F.col("is_canadian_province"), 1).otherwise(0)).alias("canadian_incidents"),
    F.count("release_substance").alias("incidents_with_release_substance"),
    F.count("volume_m3").alias("incidents_with_numeric_volume"),
    F.sum(F.when(F.col("significant_flag"), 1).otherwise(0)).alias("significant_incidents"),
    F.min("year").alias("first_year"),
    F.max("year").alias("last_year"),
)
display(save_gold(kpis, "kpis"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Incidents per year by province

# COMMAND ----------

by_year_province = (
    silver.filter(F.col("year").isNotNull())
    .groupBy("year", "province", "is_canadian_province")
    .agg(F.count("*").alias("incidents"))
    .orderBy("year", "province")
)
display(save_gold(by_year_province, "incidents_by_year_province"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Release volume by substance
# MAGIC
# MAGIC Incidents with no release ("Not Applicable") are excluded. Volumes use only the
# MAGIC incidents that have a numeric value, so `incidents_with_volume` is shown next to the median.

# COMMAND ----------

release_by_substance = (
    silver.filter(F.col("release_substance").isNotNull())
    .groupBy("release_substance")
    .agg(
        F.count("*").alias("incidents"),
        F.count("volume_m3").alias("incidents_with_volume"),
        F.expr("median(volume_m3)").alias("median_volume_m3"),
        F.sum("volume_m3").alias("total_volume_m3"),
        F.max("volume_m3").alias("max_volume_m3"),
    )
    .orderBy(F.desc("incidents"))
)
display(save_gold(release_by_substance, "release_by_substance"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Incident types by year

# COMMAND ----------

incident_types_by_year = (
    silver.filter(F.col("year").isNotNull())
    .withColumn("incident_types", F.coalesce(F.col("incident_types"), F.lit("Not recorded")))
    .groupBy("year", "incident_types")
    .agg(F.count("*").alias("incidents"))
    .orderBy("year", F.desc("incidents"))
)
display(save_gold(incident_types_by_year, "incident_types_by_year"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Causes: what happened and why

# COMMAND ----------

what = silver.select(
    F.lit("What happened").alias("dimension"),
    F.coalesce(F.col("what_happened_category"), F.lit("Not recorded")).alias("category"),
)
why = silver.select(
    F.lit("Why it happened").alias("dimension"),
    F.coalesce(F.col("why_it_happened_category"), F.lit("Not recorded")).alias("category"),
)
causes = (
    what.unionByName(why)
    .groupBy("dimension", "category")
    .agg(F.count("*").alias("incidents"))
    .orderBy("dimension", F.desc("incidents"))
)
display(save_gold(causes, "causes"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Companies with the most incidents

# COMMAND ----------

top_companies = (
    silver.withColumn("company", F.coalesce(F.col("company"), F.lit("Not recorded")))
    .groupBy("company")
    .agg(
        F.count("*").alias("incidents"),
        F.count("release_substance").alias("incidents_with_release"),
        F.sum(F.when(F.col("significant_flag"), 1).otherwise(0)).alias("significant_incidents"),
    )
    .orderBy(F.desc("incidents"))
)
display(save_gold(top_companies, "top_companies"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Significant incidents by year
# MAGIC
# MAGIC The rate uses only incidents where the flag could be read as true or false.

# COMMAND ----------

significant_by_year = (
    silver.filter(F.col("year").isNotNull())
    .groupBy("year")
    .agg(
        F.count("*").alias("incidents"),
        F.count("significant_flag").alias("incidents_with_flag"),
        F.sum(F.when(F.col("significant_flag"), 1).otherwise(0)).alias("significant_incidents"),
    )
    .withColumn(
        "significant_rate",
        F.round(F.col("significant_incidents") / F.col("incidents_with_flag"), 4),
    )
    .orderBy("year")
)
display(save_gold(significant_by_year, "significant_by_year"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Incident locations (for a map)

# COMMAND ----------

locations = (
    silver.filter(F.col("latitude").isNotNull() & F.col("longitude").isNotNull())
    .select(
        "incident_number", "year", "province", "is_canadian_province", "company",
        "incident_types", "release_substance", "volume_m3", "significant_flag",
        "latitude", "longitude",
    )
)
display(save_gold(locations, "incident_locations"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9. Export CSVs for the Streamlit app
# MAGIC
# MAGIC Writes one CSV per gold table into the `exports` folder of the `raw` volume. Download them
# MAGIC from **Catalog > workspace > default > raw > exports** and copy them into the module's
# MAGIC `data/` folder. Set `EXPORT_CSV = False` to skip this step.

# COMMAND ----------

import os

EXPORT_CSV = True
EXPORT_DIR = f"/Volumes/{CATALOG}/{SCHEMA}/raw/exports"

if EXPORT_CSV:
    os.makedirs(EXPORT_DIR, exist_ok=True)
    for name in GOLD_NAMES:
        path = f"{EXPORT_DIR}/gold_{name}.csv"
        spark.table(f"{CATALOG}.{SCHEMA}.gold_{name}").toPandas().to_csv(path, index=False)
        print("Wrote", path)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 10. Summary

# COMMAND ----------

print("Gold tables built:")
for name in GOLD_NAMES:
    print(f"  {CATALOG}.{SCHEMA}.gold_{name}")