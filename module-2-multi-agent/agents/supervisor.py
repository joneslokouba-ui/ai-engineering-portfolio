"""
Module 2: Supervisor Agent
Author: Geoffrey Jones Okwi | AI/ML Engineer
Pattern: Supervisor → routes tasks to specialist worker agents
"""

import os
from typing import Annotated, TypedDict, Literal
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

load_dotenv()

# ─────────────────────────────────────────
# SUPERVISOR STATE
# ─────────────────────────────────────────
class SupervisorState(TypedDict):
    messages:     Annotated[list[BaseMessage], add_messages]
    next_agent:   str   # which worker to call next
    task:         str   # original user task
    results:      dict  # collected results from workers
    iteration:    int


# ─────────────────────────────────────────
# SUPERVISOR SYSTEM PROMPT
# ─────────────────────────────────────────
SUPERVISOR_PROMPT = """You are a Supervisor Agent built by Geoffrey Jones Okwi.

Your job is to analyze the user's request and decide which specialist agent to call.

## YOUR TEAM OF SPECIALIST AGENTS:

1. **researcher**  — Use for: web searches, current news, finding information online,
                     "what is", "find out", "search for", "latest"

2. **analyst**     — Use for: data analysis, calculations, comparisons, job market data,
                     salary questions, skill gap analysis, "compare", "analyze", "calculate"

3. **rag_agent**   — Use for: questions about documents, tax law, regulations, policies,
                     anything that needs knowledge from stored documents

4. **FINISH**      — Use when: you have enough information to give a final answer,
                     or the question is simple enough to answer directly

## YOUR RESPONSE FORMAT:
You must respond with ONLY one of these words (nothing else):
researcher | analyst | rag_agent | FINISH

## ROUTING EXAMPLES:
- "Search for latest AI jobs" → researcher
- "What is the salary for AI Engineer?" → analyst  
- "What does the tax code say about..." → rag_agent
- "Hello, how are you?" → FINISH
- "What is 2 + 2?" → FINISH
"""


# ─────────────────────────────────────────
# SUPERVISOR NODE
# ─────────────────────────────────────────
def supervisor_node(state: SupervisorState) -> SupervisorState:
    """Supervisor decides which agent handles the task."""
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0,       # deterministic routing
        max_tokens=10,       # only needs one word
    )

    messages = [SystemMessage(content=SUPERVISOR_PROMPT)] + state["messages"]
    response = llm.invoke(messages)

    # Parse the routing decision
    decision = response.content.strip().lower()

    # Validate — default to FINISH if unexpected
    valid = {"researcher", "analyst", "rag_agent", "finish"}
    if decision not in valid:
        decision = "finish"

    return {
        **state,
        "next_agent": decision,
        "iteration": state.get("iteration", 0) + 1,}


# ─────────────────────────────────────────
# ROUTING FUNCTION
# ─────────────────────────────────────────
def route_to_agent(state: SupervisorState) -> str:
    """Route based on supervisor's decision."""
    if state.get("iteration", 0) >= 5:
        return "finish"
    return state.get("next_agent", "finish")