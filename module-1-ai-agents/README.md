# 🤖 Production AI Agent — Module 1

**Author:** Geoffrey Jones Okwi | AI/ML Engineer (Stanford/Andrew Ng)  
**Stack:** LangChain + LangGraph + Groq + Streamlit  
**Model:** llama-3.3-70b-versatile  
**Target Roles:** Applied AI Practitioner · AI Consultant · Senior AI Engineer

---

## 🏗 Architecture

```
User → Streamlit UI → Agent Core (LangGraph) → [Tools] → Response
                              ↓
                    ┌─────────────────┐
                    │  ReAct Loop     │
                    │  agent → tools  │
                    │  tools → agent  │
                    │  agent → END    │
                    └─────────────────┘
```

## 🚀 Quick Start (Windows / PyCharm)

```bash
# 1. Clone & enter project
cd production-ai-agents

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate          # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up API keys
copy .env.example .env
# Edit .env — add your GROQ_API_KEY

# 5. Run the agent (CLI test)
python agent/agent_core.py

# 6. Run Streamlit app
streamlit run app.py
```

## 🐳 Docker (Market Gap: Docker Basics)

```bash
# Build
docker build -t production-ai-agent .

# Run locally
docker run -p 8501:8501 --env-file .env production-ai-agent

# Open browser: http://localhost:8501
```

## ⚙️ CI/CD (Market Gap: CI/CD Pipelines)

GitHub Actions pipeline at `.github/workflows/ci-cd.yml`:
- **test** → runs pytest on every push
- **build** → builds & pushes Docker image to DockerHub (main branch)
- **deploy** → deploys to AWS ECS (configure secrets in repo settings)

**Required GitHub Secrets:**
```
GROQ_API_KEY
DOCKERHUB_USERNAME
DOCKERHUB_TOKEN
AWS_ACCESS_KEY_ID          # Module 2
AWS_SECRET_ACCESS_KEY      # Module 2
```

## 🛠 Tools Available

| Tool | Purpose |
|------|---------|
| `search_web` | Real-time web search (stub → Tavily in Module 2) |
| `calculate` | Safe math expression evaluator |
| `get_job_market_data` | AI/ML role market intelligence |

## 📁 Project Structure

```
production-ai-agents/
├── agent/
│   └── agent_core.py       # LangGraph ReAct agent
├── tools/                  # Extended tools (Module 2)
├── memory/                 # Persistent memory (Module 2)
├── graph/                  # Multi-agent graphs (Module 3)
├── tests/
│   └── test_agent.py       # pytest suite
├── docker/
├── .github/workflows/
│   └── ci-cd.yml           # GitHub Actions pipeline
├── app.py                  # Streamlit frontend
├── Dockerfile              # Production container
├── requirements.txt
└── .env.example
```

## 📈 Module Roadmap

- **Module 1** ← YOU ARE HERE: Single agent + tools + Docker + CI/CD
- **Module 2:** Multi-agent orchestration + real tool APIs + RAG integration
- **Module 3:** MLOps monitoring + AWS/Azure deploy + observability
- **Module 4:** Full portfolio project for $150K+ applications

---

*Built as part of a 3-week intensive AI Engineering sprint.*