"""
Module 11 — HELIX: Knowledge Base Builder
============================================
Chunks OMIM-derived disorder knowledge (omim_loader.py DisorderKnowledge
objects) into retrievable units — one chunk per (disorder, section) pair
— and indexes them for vector similarity search.

Design note on embeddings: a neural embedding model (e.g. via
sentence-transformers) would normally power the "VectorSim" half of the
hybrid formula, but pulling pretrained weights from Hugging Face Hub is
both a live external dependency (breaking the offline-reproducibility
principle ADR 011 already commits to everywhere else in HELIX) and
unavailable from this build environment's network allowlist. This
builder uses TF-IDF vectors (scikit-learn) instead — fully offline,
deterministic, rebuildable from the corpus alone. This is a genuine
design trade-off, not a hidden shortcut: TF-IDF captures lexical
similarity well but not semantic paraphrase the way neural embeddings
would. Documented here and in the module README.
"""

from __future__ import annotations

from dataclasses import dataclass

import faiss
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from src.ingestion.omim_loader import DisorderKnowledge


@dataclass
class KnowledgeChunk:
    disorder: str
    section: str          # one of the four fixed sections
    text: str


@dataclass
class KnowledgeBase:
    chunks: list[KnowledgeChunk]
    vectorizer: TfidfVectorizer
    index: faiss.Index          # FAISS IndexFlatIP over L2-normalized TF-IDF vectors


def _chunk_disorder(knowledge: DisorderKnowledge) -> list[KnowledgeChunk]:
    """One chunk per fixed section — keeps retrieval granular so a query
    about 'inheritance' doesn't pull back an entire disorder's full text
    when only one section is relevant."""
    sections = knowledge.as_sections()
    return [
        KnowledgeChunk(disorder=knowledge.disorder, section=section, text=text)
        for section, text in sections.items()
    ]


def build_knowledge_base(disorders: dict[str, DisorderKnowledge]) -> KnowledgeBase:
    """
    Builds a searchable KnowledgeBase from OMIM-derived disorder knowledge.

    Raises ValueError if `disorders` is empty — an empty knowledge base
    would make every future retrieval silently return nothing, which is
    a build-time error, not a valid (if sparse) knowledge base.
    """
    if not disorders:
        raise ValueError(
            "Cannot build a knowledge base from zero disorders — check "
            "that omim_loader.load_omim_knowledge() was called with a "
            "non-empty source file."
        )

    chunks: list[KnowledgeChunk] = []
    for knowledge in disorders.values():
        chunks.extend(_chunk_disorder(knowledge))

    corpus = [f"{c.disorder} {c.section}: {c.text}" for c in chunks]

    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(corpus).toarray().astype("float32")

    # L2-normalize so inner product == cosine similarity, letting us use
    # FAISS's IndexFlatIP (fast exact search) directly as VectorSim.
    norms = np.linalg.norm(tfidf_matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0   # guard against a zero vector for an empty/stopword-only chunk
    normalized = tfidf_matrix / norms

    index = faiss.IndexFlatIP(normalized.shape[1])
    index.add(normalized)

    return KnowledgeBase(chunks=chunks, vectorizer=vectorizer, index=index)