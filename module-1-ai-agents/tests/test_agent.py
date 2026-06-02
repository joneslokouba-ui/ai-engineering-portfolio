"""
Module 1: Agent Tests
Author: Geoffrey Jones Okwi
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from agent.agent_core import calculate, get_job_market_data, search_web


# ─── Tool Unit Tests ───────────────────────────────────────
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


class TestJobMarketTool:
    def test_ai_engineer_role(self):
        result = get_job_market_data.invoke({"role": "AI Engineer"})
        assert "LangChain" in result or "demand" in result.lower()

    def test_unknown_role_graceful(self):
        result = get_job_market_data.invoke({"role": "Underwater Basket Weaver"})
        assert "No specific data" in result or "demand" in result.lower()


class TestSearchTool:
    def test_search_returns_string(self):
        result = search_web.invoke({"query": "LangGraph tutorial 2025"})
        assert isinstance(result, str)
        assert len(result) > 0


# ─── Integration Test (requires GROQ_API_KEY) ──────────────
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