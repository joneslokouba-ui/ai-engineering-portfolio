# 🚀 Module 3: MLOps Pipeline
## Geoffrey Jones Okwi | AI Engineering Portfolio

![Module](https://img.shields.io/badge/Module-3%20MLOps-e94560?style=for-the-badge)
![Stack](https://img.shields.io/badge/Stack-MLflow%20%7C%20Prometheus%20%7C%20AWS%20ECS-0f3460?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Building-ffa500?style=for-the-badge)

---

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
| LLM | Groq — llama-3.3-70b-versatile |
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
- Log parameters, metrics, and artifacts for every run
- Compare runs across experiments
- Model registry with staging/production promotion
- Persistent experiment history

### 📈 Prometheus Monitoring
- Real-time CPU, memory, GPU metrics
- Request rate, P50/P95/P99 latency
- LLM-specific: tokens/sec, hallucination rate, cost tracking
- Configurable alerting thresholds

### ☁️ AWS ECS Deployment
- One-click Docker → ECR → ECS pipeline
- Auto health checks and stability monitoring
- Task definition management
- CloudWatch log integration

### 🔁 CI/CD Pipeline
- GitHub Actions workflow (test → build → push → deploy)
- Automated testing on every push
- Zero-downtime rolling deployments

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
├── deployment/
│   ├── __init__.py
│   └── ecs_deployer.py      # AWS ECS deployment manager
├── tests/
│   ├── __init__.py
│   └── test_all.py          # Full test suite
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