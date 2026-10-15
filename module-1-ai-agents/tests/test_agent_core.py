"""Automated tests for Module 1 (agent/agent_core.py).

Three layers:
1. Tool tests: deterministic checks of the calculator and the search placeholder.
2. Agent-loop tests: a scripted fake LLM drives the real LangGraph loop, so routing, tool execution,
   the system prompt, and the iteration cap are tested with no API key and no network.
3. Live scenario tests: real model calls, skipped unless GROQ_API_KEY is set. These are smoke tests
   (model output varies), so treat a failure as a prompt to look, not as a hard gate.

Run from the module-1-ai-agents folder:  python -m pytest -v
"""
import os
import sys
import time
import uuid
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent import agent_core  # noqa: E402
from agent.agent_core import calculate, run_agent, search_web, should_continue  # noqa: E402


# ---------------------------------------------------------------- helpers
def tool_call_message(expression: str, call_id: str | None = None) -> AIMessage:
    call_id = call_id or f"call_{uuid.uuid4().hex[:8]}"  # unique ids: LangGraph merges messages that share an id
    return AIMessage(
        content="",
        tool_calls=[{"name": "calculate", "args": {"expression": expression}, "id": call_id, "type": "tool_call"}],
    )


class ScriptedLLM:
    """Stands in for ChatGroq: returns scripted replies and records what it was sent."""

    def __init__(self, replies=(), repeat_with=None):
        self.replies = list(replies)
        self.repeat_with = repeat_with  # factory that builds a fresh reply once the script runs out
        self.calls = 0
        self.seen = []

    def bind_tools(self, tools, **kwargs):
        return self

    def invoke(self, messages):
        self.calls += 1
        self.seen.append(list(messages))
        if self.replies:
            return self.replies.pop(0)
        return self.repeat_with()


@pytest.fixture
def use_llm(monkeypatch):
    def _use(llm):
        monkeypatch.setattr(agent_core, "get_llm", lambda: llm)
        return llm

    return _use


# ---------------------------------------------------------------- 1. tool tests
@pytest.mark.parametrize(
    "expression, expected",
    [
        ("150000 * 0.15", "Result: 22500.0"),
        ("(150000 * 0.15) + 5000", "Result: 27500.0"),
        ("2 ** 10", "Result: 1024"),
        ("-5 + 3", "Result: -2"),
        ("1,000 * 2", "Result: 2000"),
        ("1,000,000 / 4", "Result: 250000.0"),
        ("1,000.50 * 2", "Result: 2001.0"),
    ],
)
def test_calculate_returns_expected_results(expression, expected):
    assert calculate.invoke({"expression": expression}) == expected


def test_calculate_rejects_unsafe_characters():
    result = calculate.invoke({"expression": "__import__('os').system('echo hi')"})
    assert result == "Error: unsafe characters in expression"


def test_calculate_reports_division_by_zero():
    assert calculate.invoke({"expression": "10 / 0"}).startswith("Calculation error")


def test_calculate_rejects_ambiguous_commas_instead_of_guessing():
    # "1,2 + 3" is not a valid thousands separator; it must not be silently evaluated as a tuple.
    assert calculate.invoke({"expression": "1,2 + 3"}) == "Error: unsupported expression"


def test_calculate_blocks_huge_exponents_quickly():
    start = time.time()
    result = calculate.invoke({"expression": "9**9**9"})
    assert result.startswith("Calculation error")
    assert time.time() - start < 1.0


def test_calculate_rejects_overlong_input():
    assert calculate.invoke({"expression": "1+" * 150 + "1"}) == "Error: expression too long"


def test_search_web_is_still_a_placeholder():
    # Documents current scope: the tool is a stub, so no test should treat it as live search.
    assert "Tavily" in search_web.invoke({"query": "AI engineer jobs"})


# ---------------------------------------------------------------- 2. agent-loop tests
def test_should_continue_routes_to_tools_when_a_tool_is_requested():
    state = {"messages": [tool_call_message("1 + 1")], "iteration": 1}
    assert should_continue(state) == "tools"


def test_should_continue_ends_on_a_plain_answer():
    state = {"messages": [AIMessage(content="Done.")], "iteration": 1}
    assert should_continue(state) == "end"


def test_should_continue_ends_at_the_iteration_cap_even_if_a_tool_is_requested():
    state = {"messages": [tool_call_message("1 + 1")], "iteration": 10}
    assert should_continue(state) == "end"


def test_direct_answer_uses_no_tool(use_llm):
    llm = use_llm(ScriptedLLM([AIMessage(content="AI Engineer demand is high.")]))
    result = run_agent("What skills do I need for an AI Engineer role?")
    assert result["answer"] == "AI Engineer demand is high."
    assert llm.calls == 1
    assert not any(isinstance(m, ToolMessage) for m in result["messages"])


def test_tool_call_is_executed_and_result_reaches_the_final_answer(use_llm):
    llm = use_llm(
        ScriptedLLM([tool_call_message("(150000 * 0.15) + 5000"), AIMessage(content="The answer is 27,500.")])
    )
    result = run_agent("Calculate: (150000 * 0.15) + 5000")
    tool_messages = [m for m in result["messages"] if isinstance(m, ToolMessage)]
    assert [m.content for m in tool_messages] == ["Result: 27500.0"]
    assert result["answer"] == "The answer is 27,500."
    assert llm.calls == 2


def test_system_prompt_is_prepended_and_limits_tools_to_one_at_a_time(use_llm):
    llm = use_llm(ScriptedLLM([AIMessage(content="ok")]))
    run_agent("Hello")
    first_message = llm.seen[0][0]
    assert isinstance(first_message, SystemMessage)
    assert "one tool at a time" in first_message.content


def test_runaway_tool_loop_stops_at_the_iteration_cap(use_llm):
    llm = use_llm(ScriptedLLM(repeat_with=lambda: tool_call_message("1 + 1")))
    run_agent("Keep calculating forever")
    assert llm.calls == 10


# ---------------------------------------------------------------- 3. live scenario tests
live = pytest.mark.skipif(not os.getenv("GROQ_API_KEY"), reason="needs GROQ_API_KEY (live model call)")


def _used_a_tool(result) -> bool:
    return any(isinstance(m, ToolMessage) for m in result["messages"])


@live
def test_live_job_skills_question_is_answered_without_a_tool():
    result = run_agent("What skills do I need for an AI Engineer role?")
    assert not _used_a_tool(result)
    assert any(skill in result["answer"] for skill in ("LangChain", "LangGraph", "Python"))


@live
def test_live_calculation_uses_the_tool_and_gets_the_number_right():
    result = run_agent("Calculate: (150000 * 0.15) + 5000")
    assert _used_a_tool(result)
    assert "27500" in result["answer"].replace(",", "")


@live
def test_live_unit_conversion_gets_the_number_right():
    result = run_agent("Convert 300 miles to kilometers")
    assert "482" in result["answer"].replace(",", "")


@live
def test_live_job_market_question_is_answered_from_the_prompt():
    result = run_agent("Job market data for AI Consultant")
    assert not _used_a_tool(result)
    assert "150" in result["answer"]