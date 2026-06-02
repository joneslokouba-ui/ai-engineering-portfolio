"""
Module 2: Researcher Agent
Author: Geoffrey Jones Okwi | AI/ML Engineer
Search: DuckDuckGo with fallback to direct LLM answer
"""

import os
import time
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

load_dotenv()


# ─────────────────────────────────────────
# DUCKDUCKGO SEARCH with retry
# ─────────────────────────────────────────
def duckduckgo_search(query: str) -> str:
    """DuckDuckGo search with retry logic."""
    try:
        from duckduckgo_search import DDGS

        # Try up to 3 times with delay (DDG rate limits)
        for attempt in range(3):
            try:
                results = []
                with DDGS() as ddgs:
                    # Try different search methods
                    for r in ddgs.text(
                        query,
                        max_results=4,
                        safesearch="off",
                        timelimit="y",   # last year results
                    ):
                        results.append(r)

                if results:
                    output = f"🔍 **Search: '{query}'**\n\n"
                    for i, r in enumerate(results, 1):
                        title = r.get("title", "No title")
                        body  = r.get("body", "")[:250]
                        href  = r.get("href", "")
                        output += f"{i}. **{title}**\n   {body}\n   🔗 {href}\n\n"
                    return output

                # No results — wait and retry
                time.sleep(2)

            except Exception as e:
                if attempt < 2:
                    time.sleep(3)
                    continue
                raise e

        return ""   # Signal to use fallback

    except ImportError:
        return "IMPORT_ERROR"
    except Exception as e:
        return f"SEARCH_ERROR: {str(e)}"


# ─────────────────────────────────────────
# RESEARCHER PROMPT
# ─────────────────────────────────────────
RESEARCHER_PROMPT = """You are a Research Specialist Agent built by Geoffrey Jones Okwi, AI/ML Engineer.

You have deep knowledge of:
- LangChain, LangGraph, and agentic AI frameworks
- AI/ML job market and career paths
- Latest AI tools and technologies (2024-2025)
- Python, Docker, AWS, MLOps

When search results are available: summarize them clearly with sources.
When answering from knowledge: be specific, accurate, and cite what you know.

Always end with 1 concrete next step.
"""


# ─────────────────────────────────────────
# RESEARCHER NODE
# ─────────────────────────────────────────
def researcher_node(state: dict) -> dict:
    """Researcher: web search + LLM synthesis with graceful fallback."""
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.2,
        max_tokens=1024,
    )

    task = state.get("task", "")

    # Step 1 — Attempt web search
    search_results = duckduckgo_search(task)

    # Step 2 — Build prompt based on search outcome
    if search_results and not search_results.startswith(("IMPORT_ERROR", "SEARCH_ERROR", "")):
        # Good results — synthesize them
        user_msg = (
            f"User question: {task}\n\n"
            f"Web search results:\n{search_results}\n\n"
            f"Summarize these results into a clear, structured answer with sources."
        )
    else:
        # Fallback — answer from LLM knowledge directly
        user_msg = (
            f"User question: {task}\n\n"
            f"Note: Web search unavailable right now. Answer from your knowledge "
            f"about LangGraph, LangChain, AI/ML, and the latest AI developments "
            f"as of 2025. Be specific and accurate."
        )

    response = llm.invoke([
        SystemMessage(content=RESEARCHER_PROMPT),
        HumanMessage(content=user_msg),
    ])

    final = response.content if hasattr(response, "content") else str(response)
    if isinstance(final, list):
        final = " ".join(
            b.get("text", "") if isinstance(b, dict) else str(b)
            for b in final
        )

    results = state.get("results", {})
    results["researcher"] = final

    return {
        **state,
        "messages":   [response],
        "results":    results,
        "next_agent": "finish",
    }