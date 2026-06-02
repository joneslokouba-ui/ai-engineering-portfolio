"""
Module 3: MLflow Experiment Tracker
Author: Geoffrey Jones Okwi | AI/ML Engineer
Purpose: Log every agent run — inputs, outputs, latency, tokens
MLOps Market Gap: Experiment tracking for production AI agents
"""

import os
import time
import uuid
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


class SimpleTracker:
    """
    JSON file-based tracker — works with zero dependencies.
    Stores every agent run locally. Can upgrade to MLflow later.
    """

    def __init__(self, log_file: str = "tracking/agent_runs.json"):
        self.log_file = log_file
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        self._runs: list = []
        self._load()

    def _load(self):
        try:
            with open(self.log_file) as f:
                self._runs = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._runs = []

    def _save(self):
        with open(self.log_file, "w") as f:
            json.dump(self._runs[-500:], f, indent=2)

    def log(self, user_input: str, agent_used: list,
            answer: str, latency_ms: float, error: str = None) -> dict:
        entry = {
            "run_id":     str(uuid.uuid4())[:8],
            "timestamp":  datetime.now().isoformat(),
            "user_input": user_input[:200],
            "agent_used": agent_used,
            "answer":     answer[:200],
            "latency_ms": round(latency_ms, 2),
            "success":    error is None,
            "error":      error,
        }
        self._runs.append(entry)
        self._save()
        self._print_summary(entry)
        return entry

    def _print_summary(self, e: dict):
        status = "SUCCESS" if e["success"] else "ERROR"
        print(f"\n{'='*50}")
        print(f"AGENT RUN [{status}]")
        print(f"  Run ID:  {e['run_id']}")
        print(f"  Agent:   {e['agent_used']}")
        print(f"  Latency: {e['latency_ms']}ms")
        print(f"{'='*50}")

    def get_history(self, limit: int = 20) -> list:
        return list(reversed(self._runs[-limit:]))

    def get_stats(self) -> dict:
        if not self._runs:
            return {"total_runs": 0, "success_rate": 0,
                    "avg_latency_ms": 0, "agent_usage": {}}
        latencies = [r["latency_ms"] for r in self._runs if r.get("latency_ms")]
        successes = [r for r in self._runs if r.get("success")]
        agents = {}
        for r in self._runs:
            for a in r.get("agent_used", []):
                agents[a] = agents.get(a, 0) + 1
        return {
            "total_runs":     len(self._runs),
            "success_rate":   round(len(successes) / len(self._runs) * 100, 1),
            "avg_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else 0,
            "agent_usage":    agents,
        }


# Global tracker instance — import this everywhere
tracker = SimpleTracker()


if __name__ == "__main__":
    print("Testing tracker...")
    t = SimpleTracker("tracking/test_runs.json")
    t.log("Salary for AI Engineer", ["analyst"], "130K-160K", 1200.5)
    t.log("Search LangGraph", ["researcher"], "Found results", 980.3)
    t.log("Calculate 150000*0.15", ["analyst"], "22500", 450.1)
    print(f"Stats: {t.get_stats()}")
    print("Tracker working!")