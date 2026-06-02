"""
Module 3: Prometheus Metrics
Author: Geoffrey Jones Okwi | AI/ML Engineer
Purpose: Real-time monitoring of agent performance
Market Gap: MLOps monitoring for production AI systems
"""

import time
from datetime import datetime
from collections import defaultdict


class AgentMetrics:
    """
    Lightweight metrics collector.
    Mirrors Prometheus counter/gauge/histogram pattern.
    Drop-in replacement until prometheus_client is installed.
    """

    def __init__(self):
        self._counters   = defaultdict(float)
        self._gauges     = defaultdict(float)
        self._histograms = defaultdict(list)
        self.start_time  = time.time()

    # ── Counters (only go up) ──────────────────
    def inc(self, name: str, value: float = 1.0, labels: dict = None):
        key = self._key(name, labels)
        self._counters[key] += value

    def get_counter(self, name: str, labels: dict = None) -> float:
        return self._counters[self._key(name, labels)]

    # ── Gauges (go up and down) ────────────────
    def set_gauge(self, name: str, value: float, labels: dict = None):
        self._gauges[self._key(name, labels)] = value

    def get_gauge(self, name: str, labels: dict = None) -> float:
        return self._gauges[self._key(name, labels)]

    # ── Histograms (distributions) ─────────────
    def observe(self, name: str, value: float, labels: dict = None):
        self._histograms[self._key(name, labels)].append(value)

    def get_histogram_stats(self, name: str, labels: dict = None) -> dict:
        data = self._histograms[self._key(name, labels)]
        if not data:
            return {"count": 0, "avg": 0, "min": 0, "max": 0, "p95": 0}
        sorted_data = sorted(data)
        p95_idx = int(len(sorted_data) * 0.95)
        return {
            "count": len(data),
            "avg":   round(sum(data) / len(data), 2),
            "min":   round(min(data), 2),
            "max":   round(max(data), 2),
            "p95":   round(sorted_data[p95_idx], 2),
        }

    def _key(self, name: str, labels: dict = None) -> str:
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def uptime_seconds(self) -> float:
        return round(time.time() - self.start_time, 1)

    def get_all_metrics(self) -> dict:
        return {
            "counters":   dict(self._counters),
            "gauges":     dict(self._gauges),
            "uptime_sec": self.uptime_seconds(),
        }


# ─────────────────────────────────────────
# GLOBAL METRICS — import this everywhere
# ─────────────────────────────────────────
metrics = AgentMetrics()

# Pre-define our key metrics
METRIC_REQUESTS_TOTAL    = "agent_requests_total"
METRIC_REQUESTS_SUCCESS  = "agent_requests_success"
METRIC_REQUESTS_ERROR    = "agent_requests_error"
METRIC_LATENCY_MS        = "agent_latency_ms"
METRIC_ACTIVE_SESSIONS   = "active_sessions"


def record_agent_call(agent_name: str, latency_ms: float, success: bool):
    """Record a single agent call — call this after every agent run."""
    metrics.inc(METRIC_REQUESTS_TOTAL,   labels={"agent": agent_name})
    metrics.observe(METRIC_LATENCY_MS,   latency_ms, labels={"agent": agent_name})

    if success:
        metrics.inc(METRIC_REQUESTS_SUCCESS, labels={"agent": agent_name})
    else:
        metrics.inc(METRIC_REQUESTS_ERROR,   labels={"agent": agent_name})


def get_dashboard_data() -> dict:
    """Return all metrics formatted for the MLOps dashboard."""
    agents = ["supervisor", "researcher", "analyst", "rag_agent", "synthesizer"]

    agent_stats = {}
    for agent in agents:
        total   = metrics.get_counter(METRIC_REQUESTS_TOTAL,   {"agent": agent})
        success = metrics.get_counter(METRIC_REQUESTS_SUCCESS, {"agent": agent})
        latency = metrics.get_histogram_stats(METRIC_LATENCY_MS, {"agent": agent})

        agent_stats[agent] = {
            "total_calls":   int(total),
            "success_calls": int(success),
            "error_calls":   int(total - success),
            "success_rate":  round((success / total * 100) if total > 0 else 0, 1),
            "latency":       latency,
        }

    total_all = sum(s["total_calls"] for s in agent_stats.values())
    success_all = sum(s["success_calls"] for s in agent_stats.values())

    return {
        "uptime_seconds": metrics.uptime_seconds(),
        "total_requests": total_all,
        "total_success":  success_all,
        "overall_success_rate": round((success_all / total_all * 100) if total_all > 0 else 0, 1),
        "agent_stats":    agent_stats,
        "timestamp":      datetime.now().isoformat(),
    }


if __name__ == "__main__":
    print("Testing metrics...")
    record_agent_call("analyst",    1200.5, True)
    record_agent_call("researcher", 980.3,  True)
    record_agent_call("analyst",    1450.2, True)
    record_agent_call("rag_agent",  2100.0, False)

    data = get_dashboard_data()
    print(f"Total requests: {data['total_requests']}")
    print(f"Success rate:   {data['overall_success_rate']}%")
    print(f"Analyst stats:  {data['agent_stats']['analyst']}")
    print("Metrics working!")