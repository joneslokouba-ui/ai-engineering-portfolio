"""Hybrid retrieval scoring: alpha * vector similarity + (1 - alpha) * keyword score.

Illustrative, dependency-free version used in Module 12 so the scoring logic can be
unit-tested locally without Databricks. The full retrieval system (FAISS + MiniLM
embeddings) lives in module-11-helix/src/rag/hybrid_rag.py; swap in that module's
keyword scorer here if you want the two to match exactly.
"""
from __future__ import annotations

import re
from typing import Iterable

_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Lower-case alphanumeric tokens."""
    return _TOKEN.findall(text.lower())


def keyword_score(query: str, text: str) -> float:
    """Fraction of distinct query tokens that appear in the text (0.0 to 1.0)."""
    q = set(tokenize(query))
    if not q:
        return 0.0
    return len(q & set(tokenize(text))) / len(q)


def hybrid_score(vector_sim: float, keyword: float, alpha: float = 0.6) -> float:
    """alpha * VectorSim + (1 - alpha) * KeywordScore, with alpha in [0, 1]."""
    if not 0.0 <= alpha <= 1.0:
        raise ValueError(f"alpha must be between 0 and 1, got {alpha}")
    return alpha * vector_sim + (1.0 - alpha) * keyword


def rank(
    query: str,
    candidates: Iterable[tuple[str, str, float]],
    alpha: float = 0.6,
) -> list[tuple[str, float]]:
    """Rank candidates, each given as (doc_id, text, vector_sim), best first."""
    scored = [
        (doc_id, hybrid_score(vec, keyword_score(query, text), alpha))
        for doc_id, text, vec in candidates
    ]
    return sorted(scored, key=lambda item: item[1], reverse=True)