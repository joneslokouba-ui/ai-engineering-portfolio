"""
AWS ECS Deployment Manager — Module 3
Geoffrey Jones Okwi | AI Engineering Portfolio
Handles Docker → ECR → ECS deployment pipeline.
"""

import json
import subprocess
import time
from datetime import datetime
from typing import Dict, List, Optional


class ECSDeployer:
    """
    Manages full Docker → ECR → ECS deployment pipeline.
    Works with real AWS credentials or simulation mode.
    """

    def __init__(
        self,
        cluster_name: str = "ai-portfolio-cluster",
        service_name: str = "module-3-mlops",
        region: str = "us-east-1",
        account_id: str = "123456789012",
        simulate: bool = True,
    ):
        self.cluster_name = cluster_name
        self.service_name = service_name
        self.region = region
        self.account_id = account_id
        self.simulate = simulate
        self.ecr_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com/{service_name}"

    # ── Docker ────────────────────────────────────────────────────────────────

    def build_image(self, tag: str = "latest", dockerfile: str = "Dockerfile") -> Dict:
        """Build Docker image."""
        cmd = f"docker build -t {self.service_name}:{tag} -f {dockerfile} ."
        return self._run_or_simulate(
            cmd=cmd,
            success_msg=f"✅ Image built: {self.service_name}:{tag}",
            step="docker_build",
        )

    def run_tests(self) -> Dict:
        """Run test suite before push."""
        cmd = "pytest tests/ -v --tb=short"
        return self._run_or_simulate(
            cmd=cmd,
            success_msg="✅ All tests passed",
            step="test",
        )

    # ── ECR ───────────────────────────────────────────────────────────────────

    def ecr_login(self) -> Dict:
        """Authenticate Docker with ECR."""
        cmd = (
            f"aws ecr get-login-password --region {self.region} | "
            f"docker login --username AWS --password-stdin {self.account_id}.dkr.ecr.{self.region}.amazonaws.com"
        )
        return self._run_or_simulate(cmd=cmd, success_msg="✅ ECR login successful", step="ecr_login")

    def push_image(self, tag: str = "latest") -> Dict:
        """Tag and push image to ECR."""
        steps = [
            f"docker tag {self.service_name}:{tag} {self.ecr_uri}:{tag}",
            f"docker push {self.ecr_uri}:{tag}",
        ]
        return self._run_or_simulate(
            cmd=" && ".join(steps),
            success_msg=f"✅ Pushed to ECR: {self.ecr_uri}:{tag}",
            step="ecr_push",
        )

    # ── ECS ───────────────────────────────────────────────────────────────────

    def update_task_definition(self, image_tag: str = "latest") -> Dict:
        """Register updated ECS task definition."""
        task_def = self._build_task_definition(image_tag)
        cmd = f"aws ecs register-task-definition --cli-input-json '{json.dumps(task_def)}'"
        return self._run_or_simulate(
            cmd=cmd,
            success_msg="✅ Task definition registered",
            step="task_def_update",
            payload=task_def,
        )

    def deploy_service(self, task_def_revision: int = 42) -> Dict:
        """Update ECS service to new task definition."""
        cmd = (
            f"aws ecs update-service "
            f"--cluster {self.cluster_name} "
            f"--service {self.service_name} "
            f"--task-definition {self.service_name}:{task_def_revision} "
            f"--force-new-deployment"
        )
        return self._run_or_simulate(
            cmd=cmd,
            success_msg=f"✅ Service updated: {self.service_name}:{task_def_revision}",
            step="ecs_deploy",
        )

    def wait_for_stability(self, timeout_seconds: int = 300) -> Dict:
        """Wait for ECS service to stabilize."""
        cmd = (
            f"aws ecs wait services-stable "
            f"--cluster {self.cluster_name} "
            f"--services {self.service_name}"
        )
        return self._run_or_simulate(
            cmd=cmd,
            success_msg="✅ Service stable — all tasks healthy",
            step="stability_check",
        )

    def health_check(self) -> Dict:
        """Run post-deploy health checks."""
        return self._run_or_simulate(
            cmd="curl -f https://module3.ai-portfolio.com/health",
            success_msg="✅ Health check passed — HTTP 200",
            step="health_check",
        )

    def full_deploy(self, tag: str = "latest") -> List[Dict]:
        """Execute complete deployment pipeline end to end."""
        pipeline = [
            ("🧪 Running tests",              self.run_tests),
            ("🐳 Building Docker image",      lambda: self.build_image(tag)),
            ("🔐 ECR authentication",         self.ecr_login),
            ("📤 Pushing image to ECR",       lambda: self.push_image(tag)),
            ("📋 Updating task definition",   lambda: self.update_task_definition(tag)),
            ("🚀 Deploying to ECS",           self.deploy_service),
            ("⏳ Waiting for stability",      self.wait_for_stability),
            ("🏥 Health check",              self.health_check),
        ]

        results = []
        for step_name, fn in pipeline:
            result = fn()
            result["step_name"] = step_name
            result["timestamp"] = datetime.now().strftime("%H:%M:%S")
            results.append(result)

            if not result.get("success"):
                result["pipeline_status"] = "FAILED"
                results.append({
                    "step_name": "❌ Pipeline aborted",
                    "success": False,
                    "message": f"Failed at: {step_name}",
                })
                return results

        results.append({
            "step_name": "✅ Deployment complete",
            "success": True,
            "message": f"Service live at https://module3.ai-portfolio.com",
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "pipeline_status": "SUCCESS",
        })
        return results

    def get_service_status(self) -> Dict:
        """Return current ECS service status."""
        return {
            "cluster": self.cluster_name,
            "service": self.service_name,
            "status": "ACTIVE",
            "running_count": 3,
            "desired_count": 3,
            "pending_count": 0,
            "task_definition": f"{self.service_name}:42",
            "load_balancer": "https://module3.ai-portfolio.com",
            "last_deployed": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "region": self.region,
        }

    # ── Internal ──────────────────────────────────────────────────────────────

    def _run_or_simulate(self, cmd: str, success_msg: str, step: str, payload: Dict = None) -> Dict:
        """Run command or simulate it based on mode."""
        result = {"step": step, "command": cmd, "payload": payload}

        if self.simulate:
            time.sleep(0.1)  # Tiny delay for realism
            result["success"] = True
            result["message"] = success_msg
            result["mode"] = "simulation"
            return result

        try:
            proc = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=300
            )
            result["success"] = proc.returncode == 0
            result["message"] = success_msg if proc.returncode == 0 else proc.stderr
            result["stdout"] = proc.stdout
            result["mode"] = "real"
        except subprocess.TimeoutExpired:
            result["success"] = False
            result["message"] = f"Timeout after 300s at step: {step}"
            result["mode"] = "real"
        except Exception as e:
            result["success"] = False
            result["message"] = str(e)
            result["mode"] = "real"

        return result

    def _build_task_definition(self, image_tag: str) -> Dict:
        """Generate ECS task definition JSON."""
        return {
            "family": self.service_name,
            "networkMode": "awsvpc",
            "requiresCompatibilities": ["FARGATE"],
            "cpu": "1024",
            "memory": "2048",
            "executionRoleArn": f"arn:aws:iam::{self.account_id}:role/ecsTaskExecutionRole",
            "containerDefinitions": [
                {
                    "name": self.service_name,
                    "image": f"{self.ecr_uri}:{image_tag}",
                    "portMappings": [{"containerPort": 8501, "protocol": "tcp"}],
                    "environment": [
                        {"name": "MODULE", "value": "3"},
                        {"name": "ENGINEER", "value": "Geoffrey Jones Okwi"},
                        {"name": "ENV", "value": "production"},
                    ],
                    "logConfiguration": {
                        "logDriver": "awslogs",
                        "options": {
                            "awslogs-group": f"/ecs/{self.service_name}",
                            "awslogs-region": self.region,
                            "awslogs-stream-prefix": "ecs",
                        },
                    },
                    "healthCheck": {
                        "command": ["CMD-SHELL", "curl -f http://localhost:8501/health || exit 1"],
                        "interval": 30,
                        "timeout": 5,
                        "retries": 3,
                    },
                }
            ],
        }