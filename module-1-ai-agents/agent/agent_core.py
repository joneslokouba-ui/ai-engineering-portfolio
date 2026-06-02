"""
Module 1: Production AI Agent Core
Author: Geoffrey Jones Okwi | AI/ML Engineer
Stack: LangChain + LangGraph + Groq (llama-3.3-70b-versatile)
FIX v2: Groq llama tool_use_failed — removed problematic tool,
         embedded knowledge in system prompt instead.
"""

import os
from typing import Annotated, TypedDict, Literal
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

load_dotenv()

# ─────────────────────────────────────────
# 1. AGENT STATE
# ─────────────────────────────────────────
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    iteration: int
    final_answer: str


# ─────────────────────────────────────────
# 2. LLM
# ─────────────────────────────────────────
def get_llm():
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.1,
        max_tokens=2048,
    )


# ─────────────────────────────────────────
# 3. TOOLS — only SAFE tools that Groq handles well
#    Job market data moved to system prompt (avoids tool_use_failed)
# ─────────────────────────────────────────
@tool
def calculate(expression: str) -> str:
    """
    Evaluate a mathematical expression.
    Input: a string with only numbers and operators like: 150000 * 0.15
    """
    try:
        allowed = set("0123456789+-*/()., ")
        if not all(c in allowed for c in expression):
            return "Error: unsafe characters in expression"
        result = eval(expression)  # noqa: S307
        return f"Result: {result}"
    except Exception as e:
        return f"Calculation error: {e}"


@tool
def search_web(query: str) -> str:
    """Search the web for current information on any topic."""
    return (
        f"[WEB SEARCH] Query: '{query}'\n"
        f"Found: Relevant AI/ML articles and job postings. "
        f"Real-time search via Tavily API coming in Module 2."
    )


TOOLS = [calculate, search_web]


# ─────────────────────────────────────────
# 4. SYSTEM PROMPT — job market data embedded here
#    so no tool call needed (avoids Groq bug)
# ─────────────────────────────────────────
SYSTEM_PROMPT = """You are a production AI Agent built by Geoffrey Jones Okwi, AI/ML Engineer (Stanford/Andrew Ng trained).

You help with AI/ML career guidance, technical questions, and calculations.

## JOB MARKET INTELLIGENCE (answer these directly — no tool needed)

**AI Engineer** — 🔥 High demand. 45K+ openings. Avg $145K/yr.
  Skills needed: LangChain, LangGraph, Docker, AWS, RAG systems, Python, FastAPI, CI/CD

**ML Engineer** — 🔥 Very high demand. 38K+ openings. Avg $155K/yr.
  Skills needed: PyTorch, TensorFlow, MLflow, Kubernetes, Spark, feature stores

**AI Consultant** — 📈 Fast growing. Remote-friendly. $150–200K contracts.
  Skills needed: Agentic AI, RAG, client delivery, cloud (AWS/Azure), LLMs, prompt engineering

**Applied AI Practitioner** — 📈 Emerging role. $130–160K. High remote availability.
  Skills needed: LangChain, HuggingFace, FAISS, vector DBs, Streamlit, Python

**Senior AI Engineer** — 💰 $170–220K. Leadership + hands-on.
  Skills needed: System design, multi-agent orchestration, MLOps, team mentoring

**Data Scientist** — ✅ Stable. 30K+ openings. Avg $125K/yr.
  Skills needed: Python, SQL, Pandas, ML, dashboards, storytelling

## TOOL USAGE RULES
- Use `calculate` tool for any math: "300 * 1.60934", "(150000 * 0.15) + 5000"
- Use `search_web` tool for current events or topics not in your knowledge
- For job market questions → answer directly from your knowledge above
- NEVER call two tools at the same time — one tool at a time only

Always be concise, accurate, and professional.
"""


# ─────────────────────────────────────────
# 5. NODES
# ─────────────────────────────────────────
def agent_node(state: AgentState) -> AgentState:
    llm = get_llm()
    llm_with_tools = llm.bind_tools(
        TOOLS,
        parallel_tool_calls=False,  # safety: one tool at a time
    )

    messages = state["messages"]
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages

    response = llm_with_tools.invoke(messages)

    return {
        "messages": [response],
        "iteration": state.get("iteration", 0) + 1,
        "final_answer": "",
    }


def should_continue(state: AgentState) -> Literal["tools", "end"]:
    last = state["messages"][-1]
    if state.get("iteration", 0) >= 10:
        return "end"
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return "end"


# ─────────────────────────────────────────
# 6. GRAPH
# ─────────────────────────────────────────
def build_agent_graph():
    tool_node = ToolNode(TOOLS)
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges(
        "agent", should_continue, {"tools": "tools", "end": END}
    )
    graph.add_edge("tools", "agent")
    return graph.compile()


# ─────────────────────────────────────────
# 7. PUBLIC INTERFACE
# ─────────────────────────────────────────
def run_agent(user_input: str, history: list[BaseMessage] | None = None) -> dict:
    app = build_agent_graph()
    messages = (history or []) + [HumanMessage(content=user_input)]
    result = app.invoke(
        {"messages": messages, "iteration": 0, "final_answer": ""},
        config={"recursion_limit": 25},
    )
    final_msg = result["messages"][-1]
    answer = final_msg.content if hasattr(final_msg, "content") else str(final_msg)
    if isinstance(answer, list):
        answer = " ".join(
            b.get("text", "") if isinstance(b, dict) else str(b) for b in answer
        )
    return {"answer": answer, "messages": result["messages"]}


# ─────────────────────────────────────────
# 8. CLI TEST
# ─────────────────────────────────────────
if __name__ == "__main__":
    print("🤖 Production AI Agent — Module 1\n")
    tests = [
        "What skills do I need for an AI Engineer role?",
        "Calculate: (150000 * 0.15) + 5000",
        "Job market data for AI Consultant",
        "Convert 300 miles to kilometers",
    ]
    for q in tests:
        print(f"USER: {q}")
        r = run_agent(q)
        print(f"AGENT: {r['answer']}\n{'─'*60}\n")