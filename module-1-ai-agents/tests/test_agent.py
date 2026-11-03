"""
Module 1: Agent Tests
Author: Geoffrey Jones Okwi

Note: job-market data now lives in the agent's system prompt (see the "FIX v2" note in agent_core.py),
so the old get_job_market_data tool tests were replaced by a system-prompt check below.
More detailed tests (calculator edge cases, agent loop with a scripted model) are in test_agent_core.py.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from agent.agent_core import calculate, search_web, SYSTEM_PROMPT


# --- Tool Unit Tests ---------------------------------------------------------
class TestCalculatorTool:
    def test_basic_addition(self):
        result = calculate.invoke({"expression": "2 + 2"})
        assert "4" in result

    def test_complex_expression(self):
        result = calculate.invoke({"expression": "150000 * 0.15"})
        assert "22500" in result

    def test_unsafe_expression_blocked(self):
        result = calculate.invoke({"expression": "import os; os.system('rm -rf /')"})
        assert "Error" in result


class TestJobMarketData:
    def test_job_market_data_is_in_the_system_prompt(self):
        assert "AI Engineer" in SYSTEM_PROMPT
        assert "LangChain" in SYSTEM_PROMPT


class TestSearchTool:
    def test_search_returns_string(self):
        result = search_web.invoke({"query": "LangGraph tutorial 2025"})
        assert isinstance(result, str)
        assert len(result) > 0


# --- Integration Test (requires GROQ_API_KEY) --------------------------------
@pytest.mark.skipif(
    not os.getenv("GROQ_API_KEY"),
    reason="Requires GROQ_API_KEY"
)
class TestAgentIntegration:
    def test_simple_question(self):
        from agent.agent_core import run_agent
        result = run_agent("What is 5 + 7?")
        assert "answer" in result
        assert len(result["answer"]) > 0

    def test_tool_use_calculation(self):
        from agent.agent_core import run_agent
        result = run_agent("Use the calculator to compute 100 * 1.5")
        assert "150" in result["answer"]