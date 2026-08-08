"""
Bastion Query Assistant — QA engine.

Wraps the HybridRetriever with a Groq LLM call to produce grounded
answers over the Bastion mineral dataset, with:

- Conversational memory (prior turns passed back into the prompt)
- Hybrid similarity scoring for retrieval (see hybrid_retriever.py)
- Source transparency (every answer lists which mineral records it
  was grounded in)

Requires GROQ_API_KEY to be set as an environment variable / Streamlit
secret at deploy time. This module does not hardcode or request a key
directly — it reads from the environment only.
"""

import os
from typing import Any, cast

from groq import Groq

from rag.hybrid_retriever import HybridRetriever

MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = (
    "You are the Bastion Query Assistant, answering questions about critical "
    "minerals using ONLY the context passages provided below. Each passage is "
    "labeled with the mineral's symbol. "
    "If the answer is not contained in the provided context, say so plainly — "
    "do not invent data. "
    "When you answer, mention which mineral(s) (by symbol and name) the answer "
    "draws from. Keep answers concise and factual."
)


class BastionQA:
    def __init__(self, minerals: list, alpha: float = 0.6, top_k: int = 4):
        self.retriever = HybridRetriever(minerals, alpha=alpha)
        self.top_k = top_k
        api_key = os.getenv("GROQ_API_KEY")
        self.client = Groq(api_key=api_key) if api_key else None

    @staticmethod
    def _build_context(retrieved: list) -> str:
        blocks = []
        for r in retrieved:
            m = r["mineral"]
            blocks.append(f"[{m['symbol']}] {r['document']}")
        return "\n\n".join(blocks)

    def answer(self, query: str, history: list | None = None):
        """
        history: list of {"role": "user"|"assistant", "content": str}
        Returns dict: {"answer": str, "sources": [...], "retrieved": [...]}
        """
        retrieved = self.retriever.retrieve(query, top_k=self.top_k)

        if not retrieved:
            return {
                "answer": (
                    "I couldn't find anything in the Bastion dataset relevant "
                    "to that question. Try rephrasing, or ask about a specific "
                    "mineral, application, or producing country."
                ),
                "sources": [],
                "retrieved": [],
            }

        if self.client is None:
            # No API key configured — fall back to retrieval-only response
            # so the tab still functions without a live LLM call.
            sources = [f"{r['mineral']['symbol']} ({r['mineral']['name']})" for r in retrieved]
            top = retrieved[0]["mineral"]
            fallback = (
                f"[Retrieval-only mode — GROQ_API_KEY not configured] "
                f"Closest match: {top['name']} ({top['symbol']}). "
                f"Applications: {', '.join(top['applications'])}. "
                f"Category: {top['category']}."
            )
            return {"answer": fallback, "sources": sources, "retrieved": retrieved}

        context = self._build_context(retrieved)
        messages = [{"role": "system", "content": f"{SYSTEM_PROMPT}\n\nContext:\n{context}"}]
        if history:
            messages.extend(history[-6:])  # last 3 turns of conversational memory
        messages.append({"role": "user", "content": query})

        completion = self.client.chat.completions.create(
            model=MODEL,
            messages=cast(Any, messages),
            temperature=0.2,
            max_tokens=500,
        )
        answer_text = completion.choices[0].message.content
        sources = [f"{r['mineral']['symbol']} ({r['mineral']['name']})" for r in retrieved]

        return {"answer": answer_text, "sources": sources, "retrieved": retrieved}