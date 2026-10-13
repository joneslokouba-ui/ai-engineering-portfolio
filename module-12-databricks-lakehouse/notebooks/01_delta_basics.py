# Databricks notebook source
# MAGIC %md
# MAGIC # 01 Delta basics
# MAGIC Create a Delta table, change it, and inspect its version history.
# MAGIC Run on Databricks Free Edition (serverless). Table name may need a `catalog.schema.` prefix.

# COMMAND ----------

df = spark.createDataFrame(
    [("well_A", 12.4), ("well_B", 15.1), ("well_C", 11.8)],
    ["well", "water_level_m"],
)
df.write.format("delta").mode("overwrite").saveAsTable("water_levels_demo")
spark.table("water_levels_demo").show()

# COMMAND ----------

spark.sql("UPDATE water_levels_demo SET water_level_m = 12.9 WHERE well = 'well_A'")
display(spark.sql("DESCRIBE HISTORY water_levels_demo"))

# COMMAND ----------

# Query an earlier version of the table (version 0 = the original write).
display(spark.sql("SELECT * FROM water_levels_demo VERSION AS OF 0"))