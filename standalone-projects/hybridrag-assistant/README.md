# 🔍 Hybrid RAG Assistant

### Geoffrey Jones Okwi | AI/ML Engineer — Standalone Project

A multi-document Retrieval-Augmented Generation (RAG) system with
conversational memory, hybrid similarity scoring, and source transparency.

---

## What it does

Ingests multiple documents into a FAISS vector store and answers questions
grounded in that corpus, citing which source(s) each answer drew from —
reducing hallucination risk and giving the user a way to verify claims.

## Key features

- **Hybrid similarity scoring** — blends dense vector similarity with
  keyword relevance (`α · VectorSim + (1−α) · KeywordScore`) rather than
  relying on embeddings alone, improving retrieval on queries with
  specific technical terms or acronyms that pure vector search can miss.
- **Conversational memory** — maintains dialogue context across turns so
  follow-up questions resolve correctly against prior exchanges.
- **Source transparency** — every answer is traceable back to the specific
  document(s) and passage(s) it was grounded in.
- **Multi-document ingestion** — not limited to a single corpus; scales
  across a document set.

## Tech stack

| Component | Technology |
|-----------|-----------|
| LLM | Groq (`llama-3.3-70b-versatile`) |
| Orchestration | LangChain |
| Vector store | FAISS |
| Embeddings | `all-MiniLM-L6-v2` |
| Deployment | Streamlit Cloud |

## Engineering notes

- Originally scaffolded from a blank Streamlit template; migrated off
  local Ollama inference to ChatGroq for cloud deployability.
- Poetry `python = "^3.11"` pin resolved a build-environment mismatch
  against Streamlit Cloud's older default Python image.

---

## Relationship to the main portfolio

This is a standalone project, separate from the `ai-engineering-portfolio`
repo's Module 2 (Supervisor + HybridRAG), even though both use the same
hybrid scoring formula. Module 2 uses hybrid scoring as one technique
inside a multi-agent Supervisor system; this repo is the full-fledged
multi-document RAG assistant itself, as its own product.

🔗 [Live demo](#) · [Portfolio index](https://github.com/joneslokouba-ui/ai-engineering-portfolio)

---

## 📬 Contact
**Geoffrey Jones Okwi** | AI/ML Engineer
- 🐙 GitHub: [joneslokouba-ui](https://github.com/joneslokouba-ui)