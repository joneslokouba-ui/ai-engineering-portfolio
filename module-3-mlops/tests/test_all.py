"""
Tests — MLflow Tracking & Monitoring
Module 3 | Geoffrey Jones Okwi | AI Engineering Portfolio
Run: pytest tests/ -v
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mlflow_tracking.tracker import MLflowTracker
from monitoring.metrics import MetricsCollector
from deployment.ecs_deployer import ECSDeployer


# ── MLflow Tracker Tests ──────────────────────────────────────────────────────

class TestMLflowTracker:
    def setup_method(self):
        self.tracker = MLflowTracker(experiment_name="test-experiment")

    def test_log_run_returns_run_id(self):
        run_id = self.tracker.log_run(
            params={"model": "llama-3.3-70b-versatile", "temperature": 0.7},
            metrics={"accuracy": 0.92, "latency_ms": 1200.0},
        )
        assert run_id is not None
        assert len(run_id) > 0

    def test_get_all_runs_accumulates(self):
        initial = len(self.tracker.get_all_runs())
        self.tracker.log_run(
            params={"model": "test-model"},
            metrics={"accuracy": 0.88},
        )
        assert len(self.tracker.get_all_runs()) == initial + 1

    def test_get_best_run(self):
        self.tracker.log_run(params={"model": "a"}, metrics={"accuracy": 0.80})
        self.tracker.log_run(params={"model": "b"}, metrics={"accuracy": 0.95})
        self.tracker.log_run(params={"model": "c"}, metrics={"accuracy": 0.87})

        best = self.tracker.get_best_run(metric="accuracy")
        assert best is not None
        assert best["accuracy"] == 0.95
        assert best["model"] == "b"

    def test_experiment_summary(self):
        self.tracker.log_run(params={"model": "x"}, metrics={"accuracy": 0.90, "latency_ms": 1000})
        summary = self.tracker.get_experiment_summary()
        assert "total_runs" in summary
        assert summary["total_runs"] >= 1
        assert "best_accuracy" in summary

    def test_compare_runs_sorted(self):
        self.tracker.log_run(params={"r": 1}, metrics={"accuracy": 0.70})
        self.tracker.log_run(params={"r": 2}, metrics={"accuracy": 0.95})
        self.tracker.log_run(params={"r": 3}, metrics={"accuracy": 0.82})

        ranked = self.tracker.compare_runs(metric="accuracy")
        accuracies = [r["accuracy"] for r in ranked]
        assert accuracies == sorted(accuracies, reverse=True)

    def test_model_registry_log(self):
        result = self.tracker.log_model_registry("llama-agent", "1.0.0", "Production")
        assert result["stage"] == "Production"
        assert result["model_name"] == "llama-agent"


# ── MetricsCollector Tests ────────────────────────────────────────────────────

class TestMetricsCollector:
    def setup_method(self):
        self.collector = MetricsCollector()

    def test_system_metrics_keys(self):
        metrics = self.collector.get_system_metrics()
        assert "cpu_pct" in metrics
        assert "mem_pct" in metrics
        assert 0 <= metrics["cpu_pct"] <= 100
        assert 0 <= metrics["mem_pct"] <= 100

    def test_request_timeseries_length(self):
        ts = self.collector.get_request_timeseries(points=30)
        assert len(ts) == 30

    def test_request_timeseries_fields(self):
        ts = self.collector.get_request_timeseries(points=5)
        for point in ts:
            assert "timestamp" in point
            assert "requests_per_min" in point
            assert "p95_latency_ms" in point

    def test_alerts_structure(self):
        alerts = self.collector.get_alerts()
        assert isinstance(alerts, list)
        assert len(alerts) >= 1
        for alert in alerts:
            assert "severity" in alert
            assert "message" in alert
            assert alert["severity"] in ["ok", "warning", "critical"]

    def test_llm_metrics(self):
        metrics = self.collector.get_llm_metrics()
        assert "total_requests_24h" in metrics
        assert "success_rate_pct" in metrics
        assert metrics["success_rate_pct"] <= 100


# ── ECS Deployer Tests ────────────────────────────────────────────────────────

class TestECSDeployer:
    def setup_method(self):
        self.deployer = ECSDeployer(simulate=True)

    def test_build_image_success(self):
        result = self.deployer.build_image(tag="test")
        assert result["success"] is True

    def test_ecr_login_success(self):
        result = self.deployer.ecr_login()
        assert result["success"] is True

    def test_full_deploy_pipeline(self):
        results = self.deployer.full_deploy(tag="latest")
        assert isinstance(results, list)
        assert len(results) > 0
        # Final result should be success
        final = results[-1]
        assert final["success"] is True
        assert "pipeline_status" in final

    def test_service_status(self):
        status = self.deployer.get_service_status()
        assert status["running_count"] == status["desired_count"]
        assert status["status"] == "ACTIVE"

    def test_task_definition_structure(self):
        task_def = self.deployer._build_task_definition("latest")
        assert "family" in task_def
        assert "containerDefinitions" in task_def
        assert len(task_def["containerDefinitions"]) == 1
        container = task_def["containerDefinitions"][0]
        assert "healthCheck" in container
        assert "logConfiguration" in container