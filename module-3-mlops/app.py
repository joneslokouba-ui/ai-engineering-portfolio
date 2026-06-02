"""
Module 3: MLOps Dashboard
Author: Geoffrey Jones Okwi | AI/ML Engineer
Shows: Live metrics, run history, agent performance, AWS deploy guide
"""

import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# Also add module-2 path for running agents
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'module-2-multi-agent'))

import streamlit as st
from tracking.mlflow_tracker import SimpleTracker
from monitoring.prometheus_metrics import record_agent_call, get_dashboard_data
from deployment.aws_deploy import print_deployment_guide, AWS_CONFIG

# ─── Page config ───────────────────────────────────────────
st.set_page_config(
    page_title="MLOps Dashboard | Geoffrey Okwi",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ───────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #0a0f1e; color: #e2e8f0; }
    .mlops-header {
        background: linear-gradient(135deg, #1a1f3a 0%, #0d1117 100%);
        border: 1px solid #2d3748;
        border-left: 4px solid #68d391;
        border-radius: 12px;
        padding: 24px 28px;
        margin-bottom: 24px;
    }
    .mlops-header h1 { color: #68d391; margin: 0; font-size: 1.8rem; }
    .mlops-header p  { color: #a0aec0; margin: 6px 0 0; }
    .metric-card {
        background: #1a1f3a; border: 1px solid #2d3748;
        border-radius: 8px; padding: 16px; text-align: center;
    }
    .metric-card .value { font-size: 1.8rem; font-weight: bold; color: #68d391; }
    .metric-card .label { font-size: 0.8rem; color: #718096; }
    .run-card {
        background: #1a2e1a; border: 1px solid #2d5a27;
        border-radius: 8px; padding: 12px; margin: 6px 0;
    }
    .run-card-error {
        background: #2e1a1a; border: 1px solid #5a2727;
        border-radius: 8px; padding: 12px; margin: 6px 0;
    }
    [data-testid="stSidebar"] { background-color: #0d1117; }
    [data-testid="stSidebar"] * { color: #e2e8f0 !important; }
    .stTabs [data-baseweb="tab"] { color: #a0aec0 !important; }
    .stTabs [aria-selected="true"] { color: #68d391 !important; }
</style>
""", unsafe_allow_html=True)

# ─── Init tracker ──────────────────────────────────────────
tracker = SimpleTracker(
    log_file=os.path.join(os.path.dirname(__file__), "tracking", "agent_runs.json")
)

# ─── Sidebar ───────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📊 MLOps Dashboard")
    st.markdown("**Module 3** — Monitoring & Deployment")
    st.markdown("---")
    st.markdown("### 🔗 Portfolio Links")
    st.markdown("**Module 1** → localhost:8501")
    st.markdown("**Module 2** → localhost:8502")
    st.markdown("**Module 3** → localhost:8503 ← HERE")
    st.markdown("---")
    st.markdown("### ⚙️ AWS Config")
    st.caption(f"Region: {AWS_CONFIG['region']}")
    st.caption(f"Cluster: {AWS_CONFIG['cluster_name']}")
    st.caption(f"CPU: {AWS_CONFIG['cpu']} | RAM: {AWS_CONFIG['memory']}MB")
    st.markdown("---")
    if st.button("🔄 Refresh Metrics", use_container_width=True):
        st.rerun()

# ─── Header ────────────────────────────────────────────────
st.markdown("""
<div class="mlops-header">
    <h1>📊 MLOps Dashboard — Module 3</h1>
    <p>Geoffrey Jones Okwi · AI/ML Engineer · Monitoring + Tracking + AWS Deployment</p>
</div>
""", unsafe_allow_html=True)

# ─── Tabs ──────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Live Metrics",
    "📋 Run History",
    "🚀 AWS Deployment",
    "🧪 Test Agent",
])


# ════════════════════════════════════════
# TAB 1 — LIVE METRICS
# ════════════════════════════════════════
with tab1:
    st.markdown("### 📈 Live Performance Metrics")

    stats = tracker.get_stats()
    dashboard = get_dashboard_data()

    # Top metrics row
    col1, col2, col3, col4, col5 = st.columns(5)
    metrics_display = [
        (str(stats.get("total_runs", 0)),            "Total Runs"),
        (f"{stats.get('success_rate', 0)}%",         "Success Rate"),
        (f"{stats.get('avg_latency_ms', 0)}ms",      "Avg Latency"),
        (str(dashboard.get("uptime_seconds", 0))+"s","Uptime"),
        ("✅",                                        "System Status"),
    ]
    for col, (val, label) in zip([col1,col2,col3,col4,col5], metrics_display):
        col.markdown(
            f'<div class="metric-card">'
            f'<div class="value">{val}</div>'
            f'<div class="label">{label}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    st.markdown("---")

    # Agent usage breakdown
    st.markdown("### 🤖 Agent Usage Breakdown")
    agent_usage = stats.get("agent_usage", {})

    if agent_usage:
        cols = st.columns(len(agent_usage))
        icons = {"analyst":"📊","researcher":"🔍","rag_agent":"📚","supervisor":"🧠"}
        for col, (agent, count) in zip(cols, agent_usage.items()):
            icon = icons.get(agent, "🤖")
            col.markdown(
                f'<div class="metric-card">'
                f'<div class="value">{count}</div>'
                f'<div class="label">{icon} {agent}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
    else:
        st.info("No agent runs recorded yet. Use the Test Agent tab to generate data.")

    st.markdown("---")

    # Monitoring explanation
    st.markdown("### 🔬 What We're Monitoring")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        **Tracked per run:**
        - ✅ User input (first 200 chars)
        - ✅ Which agent handled it
        - ✅ Response latency (ms)
        - ✅ Success / failure
        - ✅ Timestamp
        """)
    with col2:
        st.markdown("""
        **MLOps patterns used:**
        - ✅ Experiment tracking (SimpleTracker → MLflow)
        - ✅ Performance metrics (Prometheus pattern)
        - ✅ Run history & audit trail
        - ✅ Agent usage analytics
        - ✅ Error rate monitoring
        """)


# ════════════════════════════════════════
# TAB 2 — RUN HISTORY
# ════════════════════════════════════════
with tab2:
    st.markdown("### 📋 Agent Run History")

    history = tracker.get_history(limit=20)

    if not history:
        st.info("No runs yet. Go to **Test Agent** tab and run some queries!")
    else:
        st.caption(f"Showing last {len(history)} runs (most recent first)")
        for run in history:
            status_class = "run-card" if run.get("success") else "run-card-error"
            status_icon  = "✅" if run.get("success") else "❌"
            agents = ", ".join(run.get("agent_used", ["unknown"]))
            ts = run.get("timestamp", "")[:16].replace("T", " ")

            st.markdown(f"""
            <div class="{status_class}">
                {status_icon} <strong>{ts}</strong> &nbsp;|&nbsp;
                Agent: <strong>{agents}</strong> &nbsp;|&nbsp;
                Latency: <strong>{run.get('latency_ms', 0)}ms</strong><br>
                <small>Q: {run.get('user_input', '')[:100]}...</small>
            </div>
            """, unsafe_allow_html=True)


# ════════════════════════════════════════
# TAB 3 — AWS DEPLOYMENT
# ════════════════════════════════════════
with tab3:
    st.markdown("### 🚀 AWS ECS Deployment Guide")
    st.markdown("Deploy your AI portfolio to AWS — **free tier eligible!**")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        #### Architecture
        ```
        Your Code
            ↓
        Docker Image
            ↓
        AWS ECR (registry)
            ↓
        AWS ECS Fargate
            ↓
        Public URL 🌐
        ```
        """)
    with col2:
        st.markdown("""
        #### AWS Services Used
        | Service | Purpose | Cost |
        |---------|---------|------|
        | ECR | Store Docker images | Free 500MB |
        | ECS | Run containers | Free 750hrs |
        | Fargate | Serverless compute | ~$0 demo |
        | CloudWatch | Logs & monitoring | Free tier |
        """)

    st.markdown("---")
    st.markdown("#### Step-by-Step Commands")

    steps = {
        "1️⃣ Install AWS CLI": "pip install awscli\naws configure",
        "2️⃣ Build Docker Image": "docker build -t production-ai-agents .",
        "3️⃣ Create ECR Repo": "aws ecr create-repository --repository-name production-ai-agents --region us-east-1",
        "4️⃣ Push to ECR": "aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com\ndocker push <account>.dkr.ecr.us-east-1.amazonaws.com/production-ai-agents:latest",
        "5️⃣ Deploy to ECS": "aws ecs create-service --cluster ai-engineering-portfolio --service-name production-ai-agents --task-definition production-ai-agents --desired-count 1 --launch-type FARGATE",
    }
    for title, cmd in steps.items():
        with st.expander(title):
            st.code(cmd, language="bash")


# ════════════════════════════════════════
# TAB 4 — TEST AGENT (with tracking)
# ════════════════════════════════════════
with tab4:
    st.markdown("### 🧪 Test Agent — With Live Tracking")
    st.markdown("Every query here is **logged and tracked** in the Run History tab.")

    user_input = st.text_input(
        "Enter a query:",
        placeholder="e.g. What is the salary for an AI Engineer?"
    )

    if st.button("🚀 Run Agent + Track", use_container_width=True):
        if user_input.strip():
            with st.spinner("Running agent and tracking metrics..."):
                start_time = time.time()
                try:
                    from graph.multi_agent_graph import run_multi_agent
                    result     = run_multi_agent(user_input)
                    answer     = result["answer"]
                    agent_used = result["agent_used"]
                    latency_ms = (time.time() - start_time) * 1000

                    # Log to tracker
                    tracker.log(
                        user_input=user_input,
                        agent_used=agent_used,
                        answer=answer,
                        latency_ms=latency_ms,
                    )
                    # Log to metrics
                    for agent in agent_used:
                        record_agent_call(agent, latency_ms, True)

                    st.success(f"✅ Tracked! Agent: {agent_used} | Latency: {latency_ms:.0f}ms")
                    st.markdown("**Answer:**")
                    st.markdown(answer)

                except Exception as e:
                    latency_ms = (time.time() - start_time) * 1000
                    tracker.log(
                        user_input=user_input,
                        agent_used=["error"],
                        answer="",
                        latency_ms=latency_ms,
                        error=str(e),
                    )
                    st.error(f"Error: {e}")
        else:
            st.warning("Please enter a query first.")