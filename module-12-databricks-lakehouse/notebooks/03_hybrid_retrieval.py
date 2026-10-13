# Databricks notebook source
# MAGIC %md
# MAGIC # 03 Hybrid retrieval on Databricks
# MAGIC Stores a small **synthetic** document set in a Delta table, ranks it with
# MAGIC `alpha x VectorSim + (1 - alpha) x KeywordScore`, and tracks each alpha setting in MLflow.
# MAGIC
# MAGIC **Scope notes**
# MAGIC - The "vector" side here is **TF-IDF cosine similarity** (sparse vectors). Databricks Free Edition blocks
# MAGIC   outbound internet, so embedding models cannot be downloaded. In a real system, swap in dense embeddings
# MAGIC   (for example MiniLM) or a managed vector index.
# MAGIC - This is retrieval only, with no answer generation.
# MAGIC - The documents and the 10 labeled queries are synthetic and tiny. The numbers show the workflow,
# MAGIC   not real-world retrieval quality.

# COMMAND ----------

# Cell 1: store the synthetic documents in a Delta table
docs = [
    ("d1", "Benzene plume migration was delineated using monitoring wells downgradient of the former fuel storage area."),
    ("d2", "Pump test analysis estimated aquifer transmissivity with the Theis solution and drawdown observations."),
    ("d3", "In situ chemical oxidation reduced chlorinated solvent concentrations in the shallow aquifer after two injection rounds."),
    ("d4", "SAGD operations require water balance monitoring to detect possible leakage into nearby shallow groundwater."),
    ("d5", "Corrosion rate regression on inline inspection data predicts remaining wall thickness for the pipeline segment."),
    ("d6", "CUSUM control charts flag small persistent shifts in flow measurements that may indicate a pipeline leak."),
    ("d7", "Quarterly groundwater sampling results showed benzene concentrations declining at the source area wells."),
    ("d8", "Parameter estimation calibrated the groundwater model hydraulic conductivity against observed heads."),
]
spark.createDataFrame(docs, ["doc_id", "text"]).write.format("delta").mode("overwrite").saveAsTable("hybrid_docs_demo")
display(spark.table("hybrid_docs_demo"))

# COMMAND ----------

# Cell 2: scoring functions (same formula as src/hybrid_score.py) plus TF-IDF vectors
import math
import re
from collections import Counter

_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text):
    return _TOKEN.findall(text.lower())


def keyword_score(query, text):
    q = set(tokenize(query))
    if not q:
        return 0.0
    return len(q & set(tokenize(text))) / len(q)


def hybrid_score(vector_sim, keyword, alpha):
    if not 0.0 <= alpha <= 1.0:
        raise ValueError("alpha must be between 0 and 1")
    return alpha * vector_sim + (1.0 - alpha) * keyword


rows = [(r["doc_id"], r["text"]) for r in spark.table("hybrid_docs_demo").orderBy("doc_id").collect()]

n_docs = len(rows)
doc_freq = Counter()
for _, text in rows:
    doc_freq.update(set(tokenize(text)))
idf = {w: math.log((1 + n_docs) / (1 + c)) + 1 for w, c in doc_freq.items()}


def tfidf(text):
    tf = Counter(w for w in tokenize(text) if w in idf)
    return {w: c * idf[w] for w, c in tf.items()}


def cosine(a, b):
    num = sum(a[w] * b.get(w, 0.0) for w in a)
    den = math.sqrt(sum(x * x for x in a.values())) * math.sqrt(sum(x * x for x in b.values()))
    return num / den if den else 0.0


doc_vecs = {doc_id: tfidf(text) for doc_id, text in rows}


def rank(query, alpha):
    q_vec = tfidf(query)
    scored = [
        (doc_id, hybrid_score(cosine(q_vec, doc_vecs[doc_id]), keyword_score(query, text), alpha))
        for doc_id, text in rows
    ]
    return sorted(scored, key=lambda item: item[1], reverse=True)


# COMMAND ----------

# Cell 3: see how the top results change as alpha moves from keyword-only (0) to vector-only (1)
query = "groundwater benzene"
out = []
for alpha in [0.0, 0.3, 0.6, 1.0]:
    for position, (doc_id, score) in enumerate(rank(query, alpha)[:3], start=1):
        out.append((alpha, position, doc_id, round(score, 3)))
display(spark.createDataFrame(out, ["alpha", "position", "doc_id", "score"]))

# COMMAND ----------

# Cell 4: tiny labeled evaluation, one MLflow run per alpha
import mlflow

labeled_queries = [
    ("benzene plume monitoring wells", "d1"),
    ("estimate aquifer transmissivity pump test", "d2"),
    ("detect leakage SAGD water balance", "d4"),
    ("pipeline leak detection CUSUM", "d6"),
    ("remaining wall thickness corrosion", "d5"),
    ("declining benzene concentrations sampling", "d7"),
    ("groundwater model calibration", "d8"),
    ("chemical treatment of solvents in aquifer", "d3"),
    ("groundwater benzene", "d7"),
    ("water monitoring shallow", "d4"),
]

results = []
for alpha in [0.0, 0.3, 0.6, 1.0]:
    hits, reciprocal_ranks, margins = 0, [], []
    for q, expected in labeled_queries:
        ranked = rank(q, alpha)
        ids = [doc_id for doc_id, _ in ranked]
        hits += ids[0] == expected
        reciprocal_ranks.append(1.0 / (ids.index(expected) + 1))
        margins.append(ranked[0][1] - ranked[1][1])
    metrics = {
        "hit_at_1": hits / len(labeled_queries),
        "mrr": sum(reciprocal_ranks) / len(reciprocal_ranks),
        "mean_top1_margin": sum(margins) / len(margins),
    }
    with mlflow.start_run(run_name=f"hybrid_alpha_{alpha}"):
        mlflow.log_param("alpha", alpha)
        mlflow.log_param("vector_type", "tfidf_cosine")
        mlflow.log_param("n_docs", n_docs)
        mlflow.log_param("n_queries", len(labeled_queries))
        mlflow.log_metrics(metrics)
    results.append((alpha, *[round(v, 3) for v in metrics.values()]))

display(spark.createDataFrame(results, ["alpha", "hit_at_1", "mrr", "mean_top1_margin"]))

# COMMAND ----------

# MAGIC %md
# MAGIC **How to read the result:** hit@1 and MRR tie across alpha values because this corpus and these queries
# MAGIC are small and lexical, so every setting finds the right document. Only the margin between the top two
# MAGIC results changes. A real comparison needs a larger labeled set and dense embeddings.