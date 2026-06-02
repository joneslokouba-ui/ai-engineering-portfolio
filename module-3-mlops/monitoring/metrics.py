"""
Prometheus Metrics Collector — Module 3
Geoffrey Jones Okwi | AI Engineering Portfolio
Simulates production-grade monitoring for LLM pipelines.
"""

import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Graceful import — Prometheus optional for local dev
try:
    from prometheus_client import (
        Counter, Histogram, Gauge, Summary,
        start_http_server, CollectorRegistry, generate_latest
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


class MetricsCollector:
    """
    Production monitoring for LLM agent pipelines.
    Exposes Prometheus metrics + provides Streamlit-friendly data.
    """

    def __init__(self, port: int = 8000):
        self.port = port
        self.start_time = datetime.now()
        self._request_count = 0
        self._error_count = 0

        if PROMETHEUS_AVAILABLE:
            self._setup_prometheus()

    def _setup_prometheus(self):
        """Initialize Prometheus counters, gauges, histograms."""
        try:
            self.registry = CollectorRegistry()

            self.request_counter = Counter(
                "llm_requests_total",
                "Total LLM API requests",
                ["model", "status"],
                registry=self.registry,
            )
            self.latency_histogram = Histogram(
                "llm_request_latency_seconds",
                "LLM request latency in seconds",
                ["model"],
                buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
                registry=self.registry,
            )
            self.active_sessions = Gauge(
                "llm_active_sessions",
                "Number of active user sessions",
                registry=self.registry,
            )
            self.token_usage = Counter(
                "llm_tokens_total",
                "Total tokens consumed",
                ["model", "type"],
                registry=self.registry,
            )
            self.hallucination_rate = Gauge(
                "llm_hallucination_rate",
                "Rolling hallucination detection rate",
                registry=self.registry,
            )
        except Exception:
            pass  # Registry conflict in dev — safe to ignore

    # ── Public API ────────────────────────────────────────────────────────────

    def get_system_metrics(self) -> Dict[str, float]:
        """Return simulated system resource metrics."""
        return {
            "cpu_pct": round(random.uniform(18, 72), 1),
            "mem_pct": round(random.uniform(35, 68), 1),
            "disk_pct": round(random.uniform(22, 45), 1),
            "gpu_pct": round(random.uniform(0, 85), 1),
            "network_in_mbps": round(random.uniform(1, 50), 2),
            "network_out_mbps": round(random.uniform(0.5, 20), 2),
        }

    def get_request_timeseries(self, points: int = 60) -> List[Dict]:
        """Generate time-series data for the last N minutes."""
        now = datetime.now()
        data = []
        base_rps = 45

        for i in range(points):
            ts = now - timedelta(minutes=points - i)
            # Simulate traffic patterns — peak hours effect
            hour = ts.hour
            multiplier = 1.8 if 9 <= hour <= 17 else 0.6
            noise = random.uniform(0.7, 1.3)

            data.append({
                "timestamp": ts.strftime("%H:%M"),
                "requests_per_min": round(base_rps * multiplier * noise),
                "p50_latency_ms": round(random.uniform(400, 900), 1),
                "p95_latency_ms": round(random.uniform(900, 2200), 1),
                "p99_latency_ms": round(random.uniform(2000, 4500), 1),
                "error_rate_pct": round(random.uniform(0.1, 2.5), 2),
                "tokens_per_sec": round(random.uniform(30, 120), 1),
            })

        return data

    def get_alerts(self) -> List[Dict]:
        """Return current monitoring alerts."""
        alerts = [
            {
                "id": "ALT001",
                "severity": "ok",
                "message": "All ECS tasks healthy (3/3 running)",
                "triggered_at": (datetime.now() - timedelta(minutes=2)).strftime("%H:%M:%S"),
            },
            {
                "id": "ALT002",
                "severity": "ok",
                "message": "MLflow tracking server responding normally",
                "triggered_at": (datetime.now() - timedelta(minutes=1)).strftime("%H:%M:%S"),
            },
            {
                "id": "ALT003",
                "severity": "warning",
                "message": "P95 latency elevated: 1,840ms (threshold: 1,500ms)",
                "triggered_at": (datetime.now() - timedelta(minutes=8)).strftime("%H:%M:%S"),
            },
            {
                "id": "ALT004",
                "severity": "ok",
                "message": "Error rate nominal: 0.8% (threshold: 5%)",
                "triggered_at": (datetime.now() - timedelta(minutes=3)).strftime("%H:%M:%S"),
            },
        ]

        # Randomly add a critical alert for realism
        if random.random() > 0.7:
            alerts.append({
                "id": "ALT005",
                "severity": "critical",
                "message": "Memory usage spike detected: 89% on task arn:module3:task:3",
                "triggered_at": datetime.now().strftime("%H:%M:%S"),
            })

        return alerts

    def get_llm_metrics(self) -> Dict[str, Any]:
        """Return LLM-specific operational metrics."""
        return {
            "total_requests_24h": random.randint(8000, 15000),
            "success_rate_pct": round(random.uniform(97.5, 99.8), 2),
            "avg_tokens_per_request": random.randint(280, 650),
            "total_tokens_24h": random.randint(2_000_000, 8_000_000),
            "estimated_cost_24h_usd": round(random.uniform(1.20, 8.50), 2),
            "active_sessions": random.randint(5, 42),
            "cache_hit_rate_pct": round(random.uniform(18, 45), 1),
            "hallucination_rate_pct": round(random.uniform(1.5, 6.0), 2),
            "models_in_use": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"],
        }

    def record_request(self, model: str, latency_ms: float, tokens: int, success: bool = True):
        """Record a single LLM request (for real integration)."""
        self._request_count += 1
        if not success:
            self._error_count += 1

        if PROMETHEUS_AVAILABLE:
            try:
                status = "success" if success else "error"
                self.request_counter.labels(model=model, status=status).inc()
                self.latency_histogram.labels(model=model).observe(latency_ms / 1000)
                self.token_usage.labels(model=model, type="total").inc(tokens)
            except Exception:
                pass

    def start_metrics_server(self):
        """Start Prometheus HTTP metrics endpoint."""
        if PROMETHEUS_AVAILABLE:
            try:
                start_http_server(self.port, registry=self.registry)
                return f"Prometheus metrics at http://localhost:{self.port}/metrics"
            except OSError:
                return f"Port {self.port} already in use — metrics server may already be running"
        return "prometheus_client not installed — run: pip install prometheus-client"