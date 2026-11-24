# 🚀 Module 3: MLOps Pipeline
## Geoffrey Jones Okwi | AI Engineering Portfolio

![Module](https://img.shields.io/badge/Module-3%20MLOps-e94560?style=for-the-badge)
![Stack](https://img.shields.io/badge/Stack-MLflow%20%7C%20Prometheus%20%7C%20AWS%20ECS-0f3460?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Building-ffa500?style=for-the-badge)

---
## What this module is

Module 3 is an MLOps demonstration for a LangGraph LLM agent. It shows the practices around a model: experiment tracking, monitoring, packaging and a deployment design.

| Area | Status |
|---|---|
| MLflow experiment tracking | Real: parameters and metrics are logged to a local SQLite MLflow store |
| Prometheus monitoring | Real configuration and metric definitions |
| Docker | Real: Dockerfile with health check and compose files |
| Tests | `tests/test_all.py` and `tests/test_evaluation.py` |
| Run metrics (accuracy, latency, tokens, cost) | **Measured offline:** `evaluation/run_eval.py` calls the Groq API on 15 fixed questions and logs each run to MLflow |
| Monitoring tab figures (gauges, request counts, costs, alerts) | **Simulated:** randomly generated demo data |
| AWS ECS deployment | **Simulated:** no AWS resources are created |
| CI/CD | Workflow design only |


## Evaluation: measured results

`evaluation/run_eval.py` is an offline script (the public app never calls Groq). For every configuration (model x temperature) it asks 15 fixed questions with automatically checkable answers, measures response time, token counts and cost from Groq's usage figures, scores the answers, logs the run to MLflow through `MLflowTracker`, and saves `evaluation/results/eval_results.json` for the Streamlit app.

```
python -m evaluation.run_eval --limit 3   # quick smoke test
python -m evaluation.run_eval             # full run: 2 models x 2 temperatures x 15 questions
```

**Results (run on 2026-11-23, reasoning effort "low", max 2,048 completion tokens, one machine):**

| Model | Temperature | Accuracy | Median latency | Cost for 15 questions |
|---|---|---|---|---|
| openai/gpt-oss-120b | 0.0 | 100% (15/15) | 282 ms | $0.00046 |
| openai/gpt-oss-120b | 0.7 | 100% (15/15) | 295 ms | $0.00046 |
| openai/gpt-oss-20b | 0.0 | 100% (15/15) | 248 ms | $0.00024 |
| openai/gpt-oss-20b | 0.7 | 100% (15/15) | 256 ms | $0.00024 |

Cost uses Groq's list prices checked on 2026-11-23 ($0.15 and $0.60 per million input and output tokens for the 120b model, $0.075 and $0.30 for the 20b model); update `PRICES_PER_MILLION` in the script before a new run.

**How to read it**
- All four configurations answered all 15 questions correctly, so this question set is too easy to separate the models. Accuracy is at the ceiling. The run shows that the measurement and tracking pipeline works, not that the models are equally good in general.
- On this small set the 20b model had about 12-13% lower median latency and about half the cost. Latency includes network time and comes from one machine and one run, so treat it as indicative.
- Temperature made no visible difference to accuracy on these questions.
- Next steps: harder questions on which the models disagree, and repeated runs to measure variance.

## 🏗️ Architecture

```
Developer → GitHub → CodePipeline → CodeBuild → ECR → ECS Fargate
                                                         │
                                              MLflow ◄───┤
                                              Prometheus  │
                                              Grafana ◄───┘
```

## 📦 Stack

| Component | Technology |
|-----------|-----------|
| App Framework | Streamlit |
| LLM | Groq — openai/gpt-oss-120b |
| Experiment Tracking | MLflow 2.19 |
| Monitoring | Prometheus + Grafana |
| Containerization | Docker |
| Cloud | AWS ECS Fargate + ECR |
| CI/CD | GitHub Actions |
| Orchestration | LangGraph 0.2.73 |

## 🚀 Quick Start

### Local Development
```bash
# 1. Clone and enter
cd module-3-mlops

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 4. Run the app
streamlit run app/main.py
```

### Docker (Full Stack)
```bash
# Build and start all services
docker-compose up -d

# Services:
# App:        http://localhost:8501
# MLflow:     http://localhost:5000
# Prometheus: http://localhost:9090
# Grafana:    http://localhost:3000
```

### Run Tests
```bash
pytest tests/ -v
```

## 📊 Features

### 🧪 MLflow Experiment Tracking
- Logs parameters and metrics for every evaluation run to a local SQLite MLflow store
- Runs are produced by the offline evaluation script (see above)
- Runs can be compared in the MLflow UI

### 📈 Prometheus Monitoring
- Metric definitions and a scrape configuration for CPU, memory, request rate, latency, tokens per second and cost
- The dashboard's Monitoring tab shows simulated values to illustrate such a dashboard

### ☁️ AWS ECS Deployment
- A Docker to ECR to ECS flow, modelled in the dashboard as a simulation
- No AWS resources are created

### 🔁 CI/CD Pipeline
- Workflow design only (test, build, push, deploy)

## 📁 Project Structure

```
module-3-mlops/
├── app/
│   └── main.py              # Streamlit dashboard (450 lines)
├── mlflow_tracking/
│   ├── __init__.py
│   └── tracker.py           # MLflow experiment tracker
├── monitoring/
│   ├── __init__.py
│   ├── metrics.py           # Prometheus metrics collector
│   └── prometheus.yml       # Prometheus scrape config
├── evaluation/
│   ├── questions.json       # 15 fixed questions with automatic checks
│   ├── scoring.py           # answer checks, cost and summary statistics
│   ├── run_eval.py          # offline Groq evaluation, logs runs to MLflow
│   └── results/             # saved results shown in the app
├── deployment/
│   ├── __init__.py
│   └── ecs_deployer.py      # AWS ECS deployment manager
├── tests/
│   ├── __init__.py
│   ├── test_all.py          # Full test suite
│   └── test_evaluation.py   # Scoring and cost logic
├── Dockerfile               # Production container
├── docker-compose.yml       # Local dev stack
├── requirements.txt         # Python dependencies
├── .env.example             # Environment template
└── README.md
```

## 🎯 Portfolio Context

| Module | Status | Tech |
|--------|--------|------|
| 1 — Single ReAct Agent | ✅ LIVE | LangGraph · Groq · Streamlit |
| 2 — Multi-Agent System | ✅ LIVE | Supervisor · RAG · FAISS · DuckDuckGo |
| 3 — MLOps Pipeline | 🔨 Building | MLflow · Prometheus · Docker · AWS ECS |

**Target:** $150K+ AI/MLOps Engineer Role  
**Training:** Stanford / Andrew Ng · Commander Smart Eagle Program