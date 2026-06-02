"""
Module 2: Multi-Agent Orchestration Graph
Author: Geoffrey Jones Okwi | AI/ML Engineer
Pattern: Supervisor → [Researcher | Analyst | RAG Agent] → Synthesizer → END
"""

import os
from typing import Annotated, TypedDict, Literal
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from agents.supervisor import supervisor_node, route_to_agent, SupervisorState
from agents.researcher import researcher_node
from agents.analyst import analyst_node
from agents.rag_agent import rag_agent_node

load_dotenv()

# ─────────────────────────────────────────
# SYNTHESIZER — final answer composer
# ─────────────────────────────────────────
SYNTHESIZER_PROMPT = """You are a Response Synthesizer for a Multi-Agent AI System
built by Geoffrey Jones Okwi.

Your job: Take the results collected by specialist agents and compose
a clear, professional, final answer for the user.

RULES:
- Be concise and well-structured
- Use the agent results provided — don't add unsupported information
- Format with clear sections if multiple topics covered
- End with a helpful next step or recommendation
"""


def synthesizer_node(state: SupervisorState) -> SupervisorState:
    """Composes the final answer from all agent results."""
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.2,
        max_tokens=1500,
    )

    results = state.get("results", {})
    task = state.get("task", "")

    if not results:
        # No agents were called — answer directly
        messages = state["messages"]
        response = llm.invoke(
            [SystemMessage(content=SYNTHESIZER_PROMPT)] + messages
        )
    else:
        # Compose from agent results
        results_text = "\n\n".join(
            f"[{agent.upper()} AGENT RESULT]\n{content}"
            for agent, content in results.items()
        )
        prompt = (
            f"Original user request: {task}\n\n"
            f"Agent results collected:\n{results_text}\n\n"
            f"Please compose a clear, final answer for the user."
        )
        response = llm.invoke([
            SystemMessage(content=SYNTHESIZER_PROMPT),
            HumanMessage(content=prompt),
        ])

    return {
        **state,
        "messages": [response],
    }


# ─────────────────────────────────────────
# BUILD THE MULTI-AGENT GRAPH
# ─────────────────────────────────────────
def build_multi_agent_graph():
    """
    Graph topology:

    START
      ↓
    supervisor ──→ researcher ──┐
      ↓                         ↓
    supervisor ──→ analyst   ──→ synthesizer → END
      ↓                         ↑
    supervisor ──→ rag_agent ──┘
      ↓
    synthesizer → END  (if FINISH directly)
    """
    graph = StateGraph(SupervisorState)

    # Register all nodes
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("analyst", analyst_node)
    graph.add_node("rag_agent", rag_agent_node)
    graph.add_node("synthesizer", synthesizer_node)

    # Entry point
    graph.set_entry_point("supervisor")

    # Supervisor routes to specialist agents or directly to synthesizer
    graph.add_conditional_edges(
        "supervisor",
        route_to_agent,
        {
            "researcher": "researcher",
            "analyst": "analyst",
            "rag_agent": "rag_agent",
            "finish": "synthesizer",
        }
    )

    # All specialist agents → synthesizer for final answer
    graph.add_edge("researcher", "synthesizer")
    graph.add_edge("analyst", "synthesizer")
    graph.add_edge("rag_agent", "synthesizer")

    # Synthesizer → END
    graph.add_edge("synthesizer", END)

    return graph.compile()


# ─────────────────────────────────────────
# PUBLIC INTERFACE
# ─────────────────────────────────────────
def run_multi_agent(user_input: str, history: list[BaseMessage] | None = None) -> dict:
    """
    Run the full multi-agent system on a user query.

    Args:
        user_input: The user's question or task
        history:    Optional conversation history

    Returns:
        dict with 'answer', 'agent_used', 'messages'
    """
    app = build_multi_agent_graph()

    messages = (history or []) + [HumanMessage(content=user_input)]

    initial_state = {
        "messages": messages,
        "next_agent": "",
        "task": user_input,
        "results": {},
        "iteration": 0,
    }

    result = app.invoke(initial_state, config={"recursion_limit": 20})

    # Extract final answer
    final_msg = result["messages"][-1]
    answer = final_msg.content if hasattr(final_msg, "content") else str(final_msg)
    if isinstance(answer, list):
        answer = " ".join(
            b.get("text", "") if isinstance(b, dict) else str(b) for b in answer
        )

    # Which agent handled it?
    agent_used = list(result.get("results", {}).keys()) or ["supervisor"]

    return {
        "answer": answer,
        "agent_used": agent_used,
        "messages": result["messages"],
        "results": result.get("results", {}),
    }


# ─────────────────────────────────────────
# CLI TEST
# ─────────────────────────────────────────
if __name__ == "__main__":
    print("🤖 Multi-Agent System — Module 2\n")
    print("=" * 60)

    tests = [
        ("ANALYST", "What is the salary for an AI Engineer with 3 years experience?"),
        ("ANALYST", "Analyze skill gap: I know Python, Docker, LangChain. Target: AI Engineer"),
        ("CALCULATOR", "Calculate: (150000 * 0.15) + 5000"),
        ("RESEARCHER", "Search for latest LangGraph tutorials 2025"),
        ("RAG", "What does the document say about tax deductions?"),
    ]

    for expected_agent, question in tests:
        print(f"\n[Expected: {expected_agent}]")
        print(f"USER: {question}")
        result = run_multi_agent(question)
        print(f"AGENT USED: {result['agent_used']}")
        print(f"ANSWER: {result['answer'][:300]}...")
        print("-" * 60)