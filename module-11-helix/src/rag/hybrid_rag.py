"""
Module 11 — HELIX: Hybrid RAG
================================
Implements the portfolio's established hybrid retrieval formula:

    score = alpha * VectorSim(query, chunk) + (1 - alpha) * KeywordScore(query, chunk)

- VectorSim: cosine similarity over TF-IDF vectors via FAISS
  (knowledge_base_builder.py) — see that module's docstring for why
  TF-IDF rather than neural embeddings.
- KeywordScore: normalized lexical overlap between query and chunk terms.

Retrieved chunks are then passed as context to Groq's openai/gpt-oss-120b
for answer generation. (Originally llama-3.3-70b-versatile, matching the
LLM used across every other HybridRAG instance in the portfolio at the
time — migrated after Groq decommissioned that model on August 16, 2026.
See GROQ_MODEL below for details and Bastion's still-pending equivalent
update.)

Requires a GROQ_API_KEY environment variable for the generation step —
this module cannot be live-tested for generation inside a sandbox with
no network access to Groq's API; retrieval (the VectorSim + KeywordScore
half) is fully offline and IS tested. See test_hybrid_rag.py.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

import numpy as np

from src.rag.knowledge_base_builder import KnowledgeBase, KnowledgeChunk

DEFAULT_ALPHA = 0.6   # weights VectorSim slightly higher than KeywordScore,
                        # consistent with the portfolio's established default

# MODEL UPDATE (Aug 2026): llama-3.3-70b-versatile was decommissioned by
# Groq on August 16, 2026 (see Groq deprecation notice / GroqDocs
# deprecations page). Requests to it now fail with a model_decommissioned
# error. Migrated to Groq's recommended replacement, openai/gpt-oss-120b,
# per https://console.groq.com/docs/deprecations. This does NOT require a
# new API key or account change — GROQ_API_KEY works unchanged; only the
# model string changes. qwen/qwen3.6-27b is Groq's other suggested
# replacement if gpt-oss-120b's output style doesn't fit well in testing.
#
# NOTE: this same model string appears in ADR 011 and in Bastion's (Module
# 9) "Ask Bastion" assistant — both reference the now-decommissioned model
# by name and should be updated to match when next revisited.
GROQ_MODEL = "openai/gpt-oss-120b"

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


@dataclass
class ScoredChunk:
    chunk: KnowledgeChunk
    vector_sim: float
    keyword_score: float
    hybrid_score: float


class GroqAPIKeyMissingError(Exception):
    """Raised when generate_answer() is called without a GROQ_API_KEY set."""


def _keyword_score(query: str, chunk_text: str) -> float:
    """
    Normalized lexical overlap: fraction of query tokens that also
    appear in the chunk, i.e. simple recall-oriented keyword matching.
    Returns 0.0 for an empty query (no signal, not an error — the caller
    decides whether an empty query is itself invalid).
    """
    query_tokens = _tokenize(query)
    if not query_tokens:
        return 0.0
    chunk_tokens = _tokenize(chunk_text)
    overlap = query_tokens & chunk_tokens
    return len(overlap) / len(query_tokens)


def retrieve(
    query: str,
    kb: KnowledgeBase,
    alpha: float = DEFAULT_ALPHA,
    top_k: int = 3,
) -> list[ScoredChunk]:
    """
    Retrieves the top_k chunks from the knowledge base ranked by the
    hybrid score. Raises ValueError for an empty query or an alpha
    outside [0.0, 1.0] — both indicate caller error, not a valid
    (if low-quality) retrieval.
    """
    if not query.strip():
        raise ValueError("Query must not be empty.")
    if not 0.0 <= alpha <= 1.0:
        raise ValueError(f"alpha must be in [0.0, 1.0], got {alpha}")
    if top_k < 1:
        raise ValueError(f"top_k must be >= 1, got {top_k}")

    query_vec = kb.vectorizer.transform([query]).toarray().astype("float32")
    norm = np.linalg.norm(query_vec)
    if norm > 0:
        query_vec = query_vec / norm

    # FAISS returns inner products (== cosine similarity, since both
    # sides are L2-normalized) and indices into kb.chunks.
    k = min(top_k * 3, len(kb.chunks))  # over-fetch by vector score alone,
                                          # then re-rank by hybrid score below,
                                          # so a chunk with a strong keyword
                                          # match but weak vector score isn't
                                          # excluded before KeywordScore is applied
    similarities, indices = kb.index.search(query_vec, k)

    scored: list[ScoredChunk] = []
    for sim, idx in zip(similarities[0], indices[0]):
        if idx == -1:
            continue
        chunk = kb.chunks[idx]
        kw_score = _keyword_score(query, chunk.text)
        hybrid = alpha * float(sim) + (1 - alpha) * kw_score
        scored.append(
            ScoredChunk(chunk=chunk, vector_sim=float(sim), keyword_score=kw_score, hybrid_score=hybrid)
        )

    scored.sort(key=lambda s: s.hybrid_score, reverse=True)
    return scored[:top_k]


def _build_context_block(scored_chunks: list[ScoredChunk]) -> str:
    lines = []
    for sc in scored_chunks:
        lines.append(f"[{sc.chunk.disorder} — {sc.chunk.section}]\n{sc.chunk.text}")
    return "\n\n".join(lines)


_SYSTEM_PROMPT = (
    "You are the HELIX knowledge assistant, part of a genetics portfolio "
    "project. You explain and summarize published genetic disorder "
    "information provided in the CONTEXT below. You do not diagnose, "
    "manage, or give individual medical advice, and you never address "
    "the reader as if you are their clinician. If the context doesn't "
    "contain the answer, say so plainly rather than guessing."
)


def generate_answer(
    query: str,
    kb: KnowledgeBase,
    alpha: float = DEFAULT_ALPHA,
    top_k: int = 3,
    api_key: str | None = None,
) -> str:
    """
    Retrieves relevant chunks via the hybrid formula, then generates an
    answer using Groq llama-3.3-70b-versatile grounded in that context.

    Raises GroqAPIKeyMissingError if no API key is supplied and
    GROQ_API_KEY is not set in the environment — this fails loudly
    rather than silently falling back to an ungrounded model response.
    """
    key = api_key or os.environ.get("GROQ_API_KEY")
    if not key:
        raise GroqAPIKeyMissingError(
            "No Groq API key available — set GROQ_API_KEY or pass "
            "api_key explicitly. Retrieval (retrieve()) works without "
            "a key; only answer generation requires one."
        )

    scored_chunks = retrieve(query, kb, alpha=alpha, top_k=top_k)
    context = _build_context_block(scored_chunks)

    from groq import Groq   # imported lazily so retrieve() has zero
                              # dependency on the groq package being
                              # importable/configured at all

    client = Groq(api_key=key)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"CONTEXT:\n{context}\n\nQUESTION: {query}"},
        ],
    )
    return response.choices[0].message.content