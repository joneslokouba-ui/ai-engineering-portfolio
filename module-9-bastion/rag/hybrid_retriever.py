"""
Hybrid retriever for the Bastion Query Assistant.

Converts each mineral record into a flattened text passage, then scores
query relevance as:

    score = alpha * TF-IDF_cosine_similarity + (1 - alpha) * keyword_overlap

This mirrors the hybrid scoring pattern used elsewhere in the AI/ML
portfolio (Module 2 Supervisor+HybridRAG: alpha*VectorSim + (1-alpha)*
KeywordScore), applied here to the small, structured Bastion dataset —
TF-IDF stands in for dense vector similarity since the corpus is
small and structured rather than free-text documents.
"""

import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def build_document_text(mineral: dict) -> str:
    """Flatten a mineral record into a single retrievable text passage."""
    pp = mineral["physical_properties"]
    cp = mineral["chemical_properties"]
    countries = ", ".join(
        f"{c} ({s*100:.0f}%)" for c, s in mineral["producing_countries"].items()
    )
    return (
        f"{mineral['name']} ({mineral['symbol']}), category: {mineral['category']}. "
        f"Physical properties: color {pp['color']}, density {pp['density_g_cm3']} g/cm3, "
        f"melting point {pp['melting_point_c']} C. "
        f"Chemical properties: formula {cp['formula']}, reactivity: {cp['reactivity']}, "
        f"crystal structure: {cp['crystal_structure']}. "
        f"Applications: {', '.join(mineral['applications'])}. "
        f"Producing countries: {countries}. "
        f"Criticality: {mineral['criticality']}, substitutability: {mineral['substitutability']}."
    )


def _tokenize(text: str):
    return set(re.findall(r"[a-z0-9]+", text.lower()))


class HybridRetriever:
    def __init__(self, minerals: list, alpha: float = 0.6):
        self.minerals = minerals
        self.alpha = alpha
        self.documents = [build_document_text(m) for m in minerals]
        self.vectorizer = TfidfVectorizer(stop_words="english")
        self.doc_matrix = self.vectorizer.fit_transform(self.documents)
        self.doc_tokens = [_tokenize(d) for d in self.documents]

    def retrieve(self, query: str, top_k: int = 4):
        query_vec = self.vectorizer.transform([query])
        tfidf_scores = cosine_similarity(query_vec, self.doc_matrix).flatten()

        query_tokens = _tokenize(query)
        keyword_scores = []
        for tokens in self.doc_tokens:
            if not query_tokens:
                keyword_scores.append(0.0)
                continue
            overlap = len(query_tokens & tokens) / len(query_tokens)
            keyword_scores.append(overlap)

        combined = [
            self.alpha * t + (1 - self.alpha) * k
            for t, k in zip(tfidf_scores, keyword_scores)
        ]

        ranked = sorted(
            range(len(combined)), key=lambda i: combined[i], reverse=True
        )[:top_k]

        results = []
        for i in ranked:
            if combined[i] <= 0:
                continue
            results.append({
                "mineral": self.minerals[i],
                "document": self.documents[i],
                "score": round(combined[i], 4),
                "tfidf_score": round(tfidf_scores[i], 4),
                "keyword_score": round(keyword_scores[i], 4),
            })
        return results