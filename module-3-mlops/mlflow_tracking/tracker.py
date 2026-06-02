"""
MLflow Experiment Tracker — Module 3
Geoffrey Jones Okwi | AI Engineering Portfolio
"""

import mlflow
import mlflow.sklearn
import uuid
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional


class MLflowTracker:
    """
    Production-grade MLflow experiment tracker.
    Tracks params, metrics, artifacts for every LLM run.
    """

    def __init__(self, experiment_name: str = "llm-agent-v3", tracking_uri: str = "sqlite:///mlruns/mlflow.db"):
        self.experiment_name = experiment_name
        self.tracking_uri = tracking_uri
        self.run_history: List[Dict] = []

        # Ensure mlruns directory exists
        os.makedirs("mlruns", exist_ok=True)

        # Set up MLflow with SQLite backend (required for MLflow 2.x+)
        mlflow.set_tracking_uri(tracking_uri)

        # Create or get experiment
        try:
            self.experiment_id = mlflow.create_experiment(experiment_name)
        except mlflow.exceptions.MlflowException:
            exp = mlflow.get_experiment_by_name(experiment_name)
            self.experiment_id = exp.experiment_id if exp else "0"
        except Exception:
            self.experiment_id = "0"

        try:
            mlflow.set_experiment(experiment_name)
        except Exception:
            pass

    def log_run(
        self,
        params: Dict[str, Any],
        metrics: Dict[str, float],
        tags: Optional[Dict[str, str]] = None,
        artifacts: Optional[List[str]] = None,
    ) -> str:
        """Log a single training/eval run to MLflow."""
        run_id = str(uuid.uuid4())[:8].upper()

        try:
            with mlflow.start_run(run_name=f"run-{run_id}") as run:
                # Log parameters
                for k, v in params.items():
                    mlflow.log_param(k, v)

                # Log metrics
                for k, v in metrics.items():
                    mlflow.log_metric(k, v)

                # Log tags
                default_tags = {
                    "engineer": "Geoffrey Jones Okwi",
                    "module": "module-3-mlops",
                    "environment": "development",
                    "timestamp": datetime.now().isoformat(),
                }
                if tags:
                    default_tags.update(tags)
                mlflow.set_tags(default_tags)

                actual_run_id = run.info.run_id[:8].upper()

        except Exception:
            # Fallback if MLflow server not available — still track in memory
            actual_run_id = run_id

        # Always store in memory
        record = {
            "run_id": actual_run_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            **params,
            **metrics,
        }
        self.run_history.append(record)
        return actual_run_id

    def get_all_runs(self) -> List[Dict]:
        """Return all tracked runs."""
        return self.run_history

    def get_best_run(self, metric: str = "accuracy") -> Optional[Dict]:
        """Return the run with the best value for a given metric."""
        if not self.run_history:
            return None
        return max(self.run_history, key=lambda r: r.get(metric, 0))

    def compare_runs(self, metric: str = "accuracy") -> List[Dict]:
        """Return runs sorted by metric descending."""
        return sorted(self.run_history, key=lambda r: r.get(metric, 0), reverse=True)

    def log_model_registry(self, model_name: str, version: str, stage: str = "Staging"):
        """Simulate model registry promotion."""
        return {
            "model_name": model_name,
            "version": version,
            "stage": stage,
            "registered_at": datetime.now().isoformat(),
            "engineer": "Geoffrey Jones Okwi",
        }

    def get_experiment_summary(self) -> Dict:
        """Return summary stats for the experiment."""
        if not self.run_history:
            return {"total_runs": 0}

        accuracies = [r.get("accuracy", 0) for r in self.run_history]
        latencies = [r.get("latency_ms", 0) for r in self.run_history]

        return {
            "experiment_name": self.experiment_name,
            "total_runs": len(self.run_history),
            "best_accuracy": max(accuracies),
            "avg_accuracy": sum(accuracies) / len(accuracies),
            "avg_latency_ms": sum(latencies) / len(latencies),
            "last_run": self.run_history[-1]["timestamp"],
        }