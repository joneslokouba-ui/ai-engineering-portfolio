@"
# 🤖 AI Engineering Portfolio
### Geoffrey Jones Okwi | AI/ML Engineer

![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2.73-green?style=for-the-badge)
![Groq](https://img.shields.io/badge/Groq-llama--3.3--70b-orange?style=for-the-badge)
![Streamlit](https://img.shields.io/badge/Streamlit-Live-red?style=for-the-badge)
![AWS](https://img.shields.io/badge/AWS-ECS%20%7C%20ECR-yellow?style=for-the-badge&logo=amazon-aws)

> Production-grade AI engineering portfolio demonstrating end-to-end LLM systems —
> from single agents to multi-agent orchestration to full MLOps pipelines on AWS.

---

## 🚀 Live Demos

| Module | Description | Live Demo | Stack |
|--------|-------------|-----------|-------|
| 🤖 Module 1 | Production ReAct Agent | [Launch App](https://module1-ai-agents.streamlit.app) | LangGraph · Groq · Streamlit |
| 🧠 Module 2 | Multi-Agent System | [Launch App](https://module2-multi-agent.streamlit.app) | Supervisor · RAG · FAISS · DuckDuckGo |
| 🚀 Module 3 | MLOps Pipeline | [Launch App](https://module3-mlops.streamlit.app) | MLflow · Prometheus · Docker · AWS ECS |

---

## 📦 Module 1 — Production ReAct Agent
**🔗 [Live Demo](https://module1-ai-agents.streamlit.app) | [Source Code](./module-1-ai-agents)**

A production-grade ReAct (Reasoning + Acting) agent built with LangGraph and Groq.

### Features
- ⚡ Ultra-fast inference via Groq llama-3.3-70b-versatile
- 🔄 LangGraph ReAct loop with tool orchestration
- 🛠️ Tools: Web Search · Calculator · Job Market Intelligence
- 💬 Dark-theme Streamlit chat interface
- 🧠 Embedded AI job market knowledge in system prompt

### Stack
\`\`\`
LangGraph 0.2.73 · LangChain 0.3.13 · Groq · Streamlit · Python 3.11
\`\`\`

---

## 🧠 Module 2 — Multi-Agent System
**🔗 [Live Demo](https://module2-multi-agent.streamlit.app) | [Source Code](./module-2-multi-agent)**

A supervisor-pattern multi-agent system with 4 specialized agents working in concert.

### Agent Team
| Agent | Role |
|-------|------|
| 🎯 Supervisor | Routes tasks to specialist agents |
| 🔍 Researcher | DuckDuckGo web search with retry logic |
| 📊 Analyst | Salary + skill gap analysis |
| 📚 RAG Agent | HybridRAG document search (FAISS + MiniLM) |

### Signature Formula — HybridRAG
\`\`\`
Score = α · VectorSimilarity + (1-α) · KeywordScore
Vector Store: FAISS + all-MiniLM-L6-v2
\`\`\`

### Stack
\`\`\`
LangGraph 0.2.73 · LangChain 0.3.19 · Groq · FAISS · HuggingFace · DuckDuckGo · Streamlit
\`\`\`

---

## 🚀 Module 3 — MLOps Pipeline
**🔗 [Live Demo](https://module3-mlops.streamlit.app) | [Source Code](./module-3-mlops)**

A full MLOps dashboard demonstrating production ML engineering practices.

### Features
- 🧪 MLflow experiment tracking with run comparison
- 📊 Prometheus metrics — CPU · Memory · P95 Latency · Request Rate
- ☁️ AWS ECS deployment pipeline (Docker → ECR → ECS Fargate)
- 🔁 GitHub Actions CI/CD workflow
- 📈 Portfolio complexity visualization

### Stack
\`\`\`
MLflow · Prometheus · Docker · AWS ECS/ECR · GitHub Actions · Streamlit · Python 3.11
\`\`\`

---

## 🎯 Skills Demonstrated

\`\`\`
LLM Engineering    LangGraph · LangChain · Groq · Prompt Engineering
Multi-Agent        Supervisor Pattern · Tool Use · Agent Orchestration
RAG Systems        FAISS · HuggingFace · HybridRAG · Vector Search
MLOps              MLflow · Prometheus · Docker · AWS ECS · CI/CD
Frontend           Streamlit · Dark Theme UI · Interactive Dashboards
Python             Async · Type Hints · Pydantic · pytest
\`\`\`

---

## 💼 Target Roles

| Role | Salary Range |
|------|-------------|
| Senior AI/ML Engineer | \$150K+ |
| MLOps Engineer | \$140K–\$180K |
| AI Platform Engineer | \$160K+ |
| Staff AI Engineer | \$180K+ |

---

## 🏗️ Project Structure

\`\`\`
ai-engineering-portfolio/
├── module-1-ai-agents/       # ReAct Agent
│   ├── app.py                # Streamlit frontend
│   ├── agent/                # LangGraph agent core
│   └── requirements.txt
├── module-2-multi-agent/     # Multi-Agent System
│   ├── app.py                # Streamlit frontend
│   ├── agents/               # Supervisor · Researcher · Analyst · RAG
│   ├── graph/                # LangGraph orchestration
│   ├── rag/                  # HybridRAG engine
│   └── requirements.txt
├── module-3-mlops/           # MLOps Pipeline
│   ├── app/main.py           # Streamlit dashboard
│   ├── mlflow_tracking/      # Experiment tracker
│   ├── monitoring/           # Prometheus metrics
│   ├── deployment/           # AWS ECS deployer
│   ├── Dockerfile
│   └── requirements.txt
└── README.md
\`\`\`

---

## 🎓 Training & Background
- 📚 Stanford / Andrew Ng AI curriculum
- 🦅 Commander Smart Eagle Program
- 🏗️ 3-module production portfolio built in 3 weeks

---

## 📬 Contact
**Geoffrey Jones Okwi** | AI/ML Engineer
- 🐙 GitHub: [joneslokouba-ui](https://github.com/joneslokouba-ui)
- 💼 Open to: Senior AI Engineer · MLOps Engineer · AI Platform roles
"@ | Out-File -FilePath README.md -Encoding utf8
