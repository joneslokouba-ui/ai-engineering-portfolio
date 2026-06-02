"""
Module 2: RAG Agent
Author: Geoffrey Jones Okwi | AI/ML Engineer
Builds on: HybridRAG project (α·VectorSim + (1−α)·KeywordScore)
Vector Store: FAISS + HuggingFace all-MiniLM-L6-v2
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool

load_dotenv()


# ─────────────────────────────────────────
# HYBRID RAG ENGINE
# Your signature formula: α·VectorSim + (1-α)·KeywordScore
# ─────────────────────────────────────────
class HybridRAGEngine:
    """
    Hybrid retrieval combining vector similarity + keyword matching.
    Reuses Geoffrey's HybridRAG formula from previous project.
    """

    def __init__(self, alpha: float = 0.7):
        self.alpha = alpha          # weight: vector vs keyword
        self.chunks = []            # loaded document chunks
        self.embeddings = None      # HuggingFace embedder
        self.index = None           # FAISS index
        self._ready = False

    def load_documents(self, docs_path: str = "data/documents") -> bool:
        """Load documents from JSON chunks file if available."""
        try:
            from sentence_transformers import SentenceTransformer
            import faiss
            import numpy as np

            chunks_file = Path(docs_path) / "chunks.json"
            if not chunks_file.exists():
                return False

            with open(chunks_file) as f:
                self.chunks = json.load(f)

            # Build embeddings
            self.embeddings = SentenceTransformer("all-MiniLM-L6-v2")
            texts = [c["text"] for c in self.chunks]
            vectors = self.embeddings.encode(texts, show_progress_bar=False)

            # Build FAISS index
            dim = vectors.shape[1]
            self.index = faiss.IndexFlatL2(dim)
            self.index.add(vectors.astype("float32"))
            self._ready = True
            return True

        except Exception:
            return False

    def hybrid_search(self, query: str, top_k: int = 3) -> list[dict]:
        """
        Hybrid scoring: α·VectorSim + (1-α)·KeywordScore
        Geoffrey's signature formula from HybridRAG project.
        """
        if not self._ready or not self.chunks:
            return []

        import numpy as np

        # Vector similarity search
        query_vec = self.embeddings.encode([query]).astype("float32")
        distances, indices = self.index.search(query_vec, min(top_k * 3, len(self.chunks)))

        # Normalize distances to similarity scores
        max_dist = max(distances[0]) if distances[0].max() > 0 else 1
        vector_scores = {
            int(idx): 1 - (dist / max_dist)
            for idx, dist in zip(indices[0], distances[0])
            if idx >= 0
        }

        # Keyword scoring
        query_words = set(query.lower().split())
        keyword_scores = {}
        for i, chunk in enumerate(self.chunks):
            chunk_words = set(chunk["text"].lower().split())
            overlap = len(query_words & chunk_words)
            keyword_scores[i] = overlap / max(len(query_words), 1)

        # Hybrid formula: α·VectorSim + (1−α)·KeywordScore
        hybrid = {}
        for idx in vector_scores:
            v_score = vector_scores.get(idx, 0)
            k_score = keyword_scores.get(idx, 0)
            hybrid[idx] = self.alpha * v_score + (1 - self.alpha) * k_score

        # Sort and return top_k
        top_indices = sorted(hybrid, key=hybrid.get, reverse=True)[:top_k]
        return [
            {**self.chunks[i], "score": round(hybrid[i], 4)}
            for i in top_indices
        ]


# Global RAG engine instance
_rag_engine = HybridRAGEngine(alpha=0.7)


# ─────────────────────────────────────────
# RAG TOOL
# ─────────────────────────────────────────
@tool
def query_documents(question: str) -> str:
    """
    Search through loaded documents using HybridRAG.
    Use for: tax questions, policy documents, regulations,
    or any stored knowledge base queries.
    """
    global _rag_engine

    # Try to load documents if not ready
    if not _rag_engine._ready:
        loaded = _rag_engine.load_documents()
        if not loaded:
            # Graceful fallback — no documents loaded yet
            return (
                f"[RAG] No documents loaded yet for query: '{question}'\n"
                f"📁 To add documents:\n"
                f"   1. Create folder: module-2-multi-agent/data/documents/\n"
                f"   2. Add your chunks.json file (from Tax RAG project)\n"
                f"   3. The agent will auto-load and search them\n\n"
                f"💡 Your Tax RAG Assistant (268 pages, 3,797 chunks) "
                f"can be plugged in here directly!"
            )

    results = _rag_engine.hybrid_search(question, top_k=3)

    if not results:
        return f"No relevant documents found for: '{question}'"

    output = f"📚 RAG Results for: '{question}'\n"
    output += f"Formula: α({_rag_engine.alpha})·VectorSim + (1-α)·KeywordScore\n\n"

    for i, r in enumerate(results, 1):
        output += f"**Result {i}** (score: {r['score']})\n"
        output += f"{r.get('text', '')[:300]}...\n\n"

    return output


RAG_TOOLS = [query_documents]


# ─────────────────────────────────────────
# RAG AGENT PROMPT
# ─────────────────────────────────────────
RAG_PROMPT = """You are a Document Intelligence Agent built by Geoffrey Jones Okwi.

You have access to a HybridRAG system using:
- FAISS vector store (semantic search)
- Keyword matching
- Hybrid formula: α·VectorSim + (1-α)·KeywordScore

Your job: Search documents and answer questions accurately.

RULES:
- Always use query_documents tool first
- Cite which document section you found the answer in
- If no relevant docs found, say so clearly
- Never make up information — only use what's in the documents
"""


# ─────────────────────────────────────────
# RAG AGENT NODE
# ─────────────────────────────────────────
def rag_agent_node(state: dict) -> dict:
    """RAG agent — searches document knowledge base."""
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0,
        max_tokens=1024,
    )
    llm_with_tools = llm.bind_tools(RAG_TOOLS, parallel_tool_calls=False)

    task = state.get("task", "")
    messages = [
        SystemMessage(content=RAG_PROMPT),
        HumanMessage(content=task),
    ]

    for _ in range(3):
        response = llm_with_tools.invoke(messages)
        messages.append(response)

        if not (hasattr(response, "tool_calls") and response.tool_calls):
            break

        for tc in response.tool_calls:
            if tc["name"] == "query_documents":
                result = query_documents.invoke(tc["args"])
                messages.append(ToolMessage(content=result, tool_call_id=tc["id"]))

    final = messages[-1].content if hasattr(messages[-1], "content") else str(messages[-1])
    if isinstance(final, list):
        final = " ".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in final)

    results = state.get("results", {})
    results["rag_agent"] = final

    return {
        **state,
        "messages": [response],
        "results": results,
        "next_agent": "finish",
    }