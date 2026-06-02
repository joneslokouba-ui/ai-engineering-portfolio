"""
Module 3: AWS Deployment Guide
Author: Geoffrey Jones Okwi | AI/ML Engineer
Target: AWS ECS (Elastic Container Service)
Market Gap: AWS fundamentals for AI Engineers
"""

import os
import json
import subprocess
from datetime import datetime


# ─────────────────────────────────────────
# AWS ECS DEPLOYMENT CONFIGURATION
# ─────────────────────────────────────────
AWS_CONFIG = {
    "region":          "us-east-1",
    "account_id":      os.getenv("AWS_ACCOUNT_ID", "123456789012"),
    "cluster_name":    "ai-engineering-portfolio",
    "service_name":    "production-ai-agents",
    "image_name":      "production-ai-agents",
    "container_port":  8501,
    "cpu":             "512",      # 0.5 vCPU
    "memory":          "1024",     # 1GB RAM
    "desired_count":   1,
}


# ─────────────────────────────────────────
# ECS TASK DEFINITION
# This is what AWS uses to run your container
# ─────────────────────────────────────────
def generate_task_definition() -> dict:
    """Generate AWS ECS task definition JSON."""
    ecr_uri = (
        f"{AWS_CONFIG['account_id']}.dkr.ecr."
        f"{AWS_CONFIG['region']}.amazonaws.com/"
        f"{AWS_CONFIG['image_name']}:latest"
    )

    return {
        "family": AWS_CONFIG["service_name"],
        "networkMode": "awsvpc",
        "requiresCompatibilities": ["FARGATE"],
        "cpu":    AWS_CONFIG["cpu"],
        "memory": AWS_CONFIG["memory"],
        "executionRoleArn": f"arn:aws:iam::{AWS_CONFIG['account_id']}:role/ecsTaskExecutionRole",
        "containerDefinitions": [
            {
                "name":  AWS_CONFIG["service_name"],
                "image": ecr_uri,
                "portMappings": [
                    {
                        "containerPort": AWS_CONFIG["container_port"],
                        "protocol": "tcp"
                    }
                ],
                "environment": [
                    {"name": "GROQ_API_KEY",    "value": os.getenv("GROQ_API_KEY", "")},
                    {"name": "STREAMLIT_SERVER_HEADLESS", "value": "true"},
                ],
                "logConfiguration": {
                    "logDriver": "awslogs",
                    "options": {
                        "awslogs-group":         f"/ecs/{AWS_CONFIG['service_name']}",
                        "awslogs-region":        AWS_CONFIG["region"],
                        "awslogs-stream-prefix": "ecs"
                    }
                },
                "healthCheck": {
                    "command": [
                        "CMD-SHELL",
                        f"curl -f http://localhost:{AWS_CONFIG['container_port']}/_stcore/health || exit 1"
                    ],
                    "interval": 30,
                    "timeout":  10,
                    "retries":  3,
                }
            }
        ]
    }


# ─────────────────────────────────────────
# DEPLOYMENT STEPS — printed as guide
# ─────────────────────────────────────────
def print_deployment_guide():
    """Print step-by-step AWS deployment guide."""
    ecr_uri = (
        f"{AWS_CONFIG['account_id']}.dkr.ecr."
        f"{AWS_CONFIG['region']}.amazonaws.com/"
        f"{AWS_CONFIG['image_name']}"
    )

    guide = f"""
╔══════════════════════════════════════════════════════════╗
║     AWS ECS DEPLOYMENT GUIDE                            ║
║     Geoffrey Jones Okwi | AI/ML Engineer                ║
╚══════════════════════════════════════════════════════════╝

PREREQUISITES:
  1. AWS CLI installed: pip install awscli
  2. Configure: aws configure (enter your access keys)
  3. Docker Desktop running

STEP 1 — Build Docker Image
─────────────────────────────
  docker build -t {AWS_CONFIG['image_name']} .

STEP 2 — Create ECR Repository (AWS Container Registry)
─────────────────────────────────────────────────────────
  aws ecr create-repository \\
    --repository-name {AWS_CONFIG['image_name']} \\
    --region {AWS_CONFIG['region']}

STEP 3 — Push Image to ECR
───────────────────────────
  # Login to ECR
  aws ecr get-login-password --region {AWS_CONFIG['region']} | \\
    docker login --username AWS --password-stdin {ecr_uri}

  # Tag image
  docker tag {AWS_CONFIG['image_name']}:latest {ecr_uri}:latest

  # Push
  docker push {ecr_uri}:latest

STEP 4 — Create ECS Cluster
──────────────────────────────
  aws ecs create-cluster \\
    --cluster-name {AWS_CONFIG['cluster_name']} \\
    --region {AWS_CONFIG['region']}

STEP 5 — Register Task Definition
────────────────────────────────────
  aws ecs register-task-definition \\
    --cli-input-json file://deployment/task-definition.json

STEP 6 — Create Service
─────────────────────────
  aws ecs create-service \\
    --cluster {AWS_CONFIG['cluster_name']} \\
    --service-name {AWS_CONFIG['service_name']} \\
    --task-definition {AWS_CONFIG['service_name']} \\
    --desired-count {AWS_CONFIG['desired_count']} \\
    --launch-type FARGATE \\
    --network-configuration "awsvpcConfiguration={{
      subnets=[subnet-xxxxx],
      securityGroups=[sg-xxxxx],
      assignPublicIp=ENABLED
    }}"

STEP 7 — Get Public URL
─────────────────────────
  aws ecs describe-tasks \\
    --cluster {AWS_CONFIG['cluster_name']} \\
    --tasks $(aws ecs list-tasks \\
      --cluster {AWS_CONFIG['cluster_name']} \\
      --query 'taskArns[0]' --output text)

FREE TIER COSTS (first 12 months):
  ECS Fargate:  ~$0 (750 hours/month free)
  ECR Storage:  ~$0 (500MB free)
  Total:        ~$0 for portfolio/demo use
"""
    print(guide)
    return guide


# ─────────────────────────────────────────
# DOCKER COMPOSE — local multi-container
# ─────────────────────────────────────────
def generate_docker_compose() -> str:
    """Generate docker-compose.yml for local MLOps stack."""
    return """version: '3.8'

services:
  # Module 1 — Single Agent
  module-1:
    build: ../module-1-ai-agents
    ports:
      - "8501:8501"
    env_file: ../module-1-ai-agents/.env
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8501/_stcore/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Module 2 — Multi-Agent System
  module-2:
    build: ../module-2-multi-agent
    ports:
      - "8502:8501"
    env_file: ../module-2-multi-agent/.env
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8501/_stcore/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Module 3 — MLOps Dashboard
  module-3:
    build: .
    ports:
      - "8503:8501"
    volumes:
      - ./tracking:/app/tracking
    env_file: .env

networks:
  default:
    name: ai-portfolio-network
"""


# ─────────────────────────────────────────
# SAVE DEPLOYMENT FILES
# ─────────────────────────────────────────
def save_deployment_files():
    """Save task definition and docker-compose to disk."""
    os.makedirs("deployment", exist_ok=True)
    os.makedirs("docker",     exist_ok=True)

    # Save task definition
    task_def = generate_task_definition()
    with open("deployment/task-definition.json", "w") as f:
        json.dump(task_def, f, indent=2)
    print("Saved: deployment/task-definition.json")

    # Save docker-compose
    compose = generate_docker_compose()
    with open("docker/docker-compose.yml", "w") as f:
        f.write(compose)
    print("Saved: docker/docker-compose.yml")


if __name__ == "__main__":
    print_deployment_guide()
    save_deployment_files()
    print("\nAWS deployment files ready!")