"""
Module 3: MLOps Pipeline — Geoffrey Jones Okwi
AI Engineering Portfolio | MLflow + Prometheus + AWS ECS
"""

import sys
import os

# ── Path fix: works from root, app/, or PyCharm run config ───────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))   # .../app/
_ROOT = os.path.dirname(_HERE)                        # .../module-3-mlops/
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import streamlit as st
import time
import random
import json
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from mlflow_tracking.tracker import MLflowTracker
from monitoring.metrics import MetricsCollector

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MLOps Pipeline Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 2rem; border-radius: 12px; margin-bottom: 1.5rem;
        border: 1px solid #e94560;
    }
    .metric-card {
        background: #16213e; padding: 1.2rem; border-radius: 10px;
        border-left: 4px solid #e94560; margin-bottom: 1rem;
    }
    .status-live { color: #00ff88; font-weight: bold; }
    .status-warn { color: #ffa500; font-weight: bold; }
    .status-error { color: #ff4444; font-weight: bold; }
    .pipeline-step {
        background: #0f3460; padding: 0.8rem 1.2rem; border-radius: 8px;
        margin: 0.3rem 0; border: 1px solid #1a4a8a;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1 style="color:#e94560; margin:0">🚀 Module 3: MLOps Pipeline</h1>
    <p style="color:#a0aec0; margin:0.5rem 0 0">
        Geoffrey Jones Okwi · AI Engineering Portfolio · MLflow + Prometheus + AWS ECS
    </p>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Pipeline Control")
    st.markdown("---")

    experiment_name = st.text_input("Experiment Name", value="llm-agent-v3")
    st.caption("The MLflow Tracking tab shows results measured offline against the Groq API.")
    enable_monitoring = st.toggle("Enable Prometheus Monitoring", value=True)
    enable_aws = st.toggle("Simulate AWS ECS Deploy", value=True)

    st.markdown("---")
    st.markdown("### 📦 Portfolio")
    st.success("✅ Module 1 — LIVE")
    st.success("✅ Module 2 — LIVE")
    st.warning("🔨 Module 3 — DEMO")

    st.markdown("---")
    st.markdown("**Target:** `AI Engineer`")
    st.markdown("**Stack:** LangGraph · Groq · Docker · AWS")

# ── Initialize components ─────────────────────────────────────────────────────
tracker = MLflowTracker(experiment_name=experiment_name)
metrics_collector = MetricsCollector()

RESULTS_DIR = Path(_ROOT) / "evaluation" / "results"


def load_eval_results():
    """Saved output of `python -m evaluation.run_eval`, or None if it has not been run."""
    path = RESULTS_DIR / "eval_results.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))

# ── Main tabs ─────────────────────────────────────────────────────────────────
st.info(
    "Measured vs simulated: the MLflow Tracking tab shows results measured offline against the "
    "Groq API on a small question set. The Monitoring figures and the ECS deployment are simulated "
    "demos, and no AWS resources are created."
)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🧪 MLflow Tracking",
    "📊 Monitoring",
    "☁️ AWS Deployment",
    "🔁 CI/CD Pipeline",
    "📈 Portfolio Stats"
])

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 1 — MLflow Tracking
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab1:
    st.subheader("🧪 MLflow Experiment Tracking")

    eval_data = load_eval_results()
    if eval_data is None:
        st.info(
            "No evaluation results found. Run `python -m evaluation.run_eval` from the "
            "module-3-mlops folder, then commit evaluation/results/."
        )
    else:
        runs_df = pd.DataFrame(eval_data["runs"])
        qset = eval_data["question_set"]
        st.caption(
            f"Measured on {eval_data['evaluated_at'][:10]} against the Groq API using "
            f"{qset['n_questions']} fixed questions. Prices checked {eval_data['prices_checked']}."
        )

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Runs measured", len(runs_df))
        col2.metric("Best accuracy", f"{runs_df['accuracy'].max():.0%}")
        col3.metric("Median latency", f"{runs_df['latency_ms_p50'].median() / 1000:.2f} s")
        col4.metric("Total cost", f"${runs_df['cost_usd_total'].sum():.4f}")

        st.markdown("---")
        table = runs_df[[
            "run_id", "model", "temperature", "accuracy", "latency_ms_p50", "latency_ms_p95",
            "tokens_per_sec_mean", "completion_tokens_total", "cost_usd_total", "error_count",
        ]].round(4)
        st.dataframe(table, use_container_width=True, hide_index=True)

        chart_df = runs_df.assign(config=runs_df["model"].str.split("/").str[-1] + " t=" + runs_df["temperature"].astype(str))
        left, right = st.columns(2)
        with left:
            fig_acc = px.bar(chart_df, x="config", y="accuracy", title="Accuracy by configuration",
                             color_discrete_sequence=["#e94560"])
            fig_acc.update_layout(paper_bgcolor="#16213e", plot_bgcolor="#0f3460", font_color="white",
                                  xaxis_title="", yaxis_title="Accuracy", yaxis_range=[0, 1])
            st.plotly_chart(fig_acc, use_container_width=True)
        with right:
            fig_lat = px.bar(chart_df, x="config", y="latency_ms_p50", title="Median latency (ms)",
                             color_discrete_sequence=["#4cc9f0"])
            fig_lat.update_layout(paper_bgcolor="#16213e", plot_bgcolor="#0f3460", font_color="white",
                                  xaxis_title="", yaxis_title="Milliseconds")
            st.plotly_chart(fig_lat, use_container_width=True)

        details_path = RESULTS_DIR / "eval_details.csv"
        if details_path.exists():
            with st.expander("Per-question results"):
                st.dataframe(pd.read_csv(details_path), use_container_width=True, hide_index=True)

        st.caption(eval_data["notes"] + " With only a few questions, treat the comparison as a demonstration "
                   "of the method, not a benchmark.")

    st.markdown("### 📋 Experiment History")
    st.caption(
        "Each configuration is logged as an MLflow run (parameters and metrics) in a local MLflow store "
        "when the evaluation script runs. This app displays the saved results file."
    )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 2 — Monitoring
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab2:
    st.subheader("📊 Prometheus Metrics & Monitoring")
    st.warning(
        "Simulated data: the gauges, request counts, costs and rates on this tab are randomly generated "
        "to demonstrate what a monitoring dashboard looks like. They are not measurements of any live service."
    )

    if enable_monitoring:
        st.markdown('<span class="status-live">● MONITORING DEMO (SIMULATED DATA)</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-warn">● MONITORING DISABLED</span>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### System Metrics")
        system_data = metrics_collector.get_system_metrics()
        fig_sys = go.Figure()
        fig_sys.add_trace(go.Indicator(
            mode="gauge+number+delta",
            value=system_data["cpu_pct"],
            title={"text": "CPU Usage %"},
            delta={"reference": 50},
            gauge={"axis": {"range": [0, 100]},
                   "bar": {"color": "#e94560"},
                   "steps": [{"range": [0, 50], "color": "#1a4a8a"},
                              {"range": [50, 80], "color": "#ffa500"},
                              {"range": [80, 100], "color": "#ff4444"}]},
        ))
        fig_sys.update_layout(paper_bgcolor="#16213e", font_color="white", height=250)
        st.plotly_chart(fig_sys, use_container_width=True)

        fig_mem = go.Figure()
        fig_mem.add_trace(go.Indicator(
            mode="gauge+number+delta",
            value=system_data["mem_pct"],
            title={"text": "Memory Usage %"},
            delta={"reference": 60},
            gauge={"axis": {"range": [0, 100]},
                   "bar": {"color": "#00ff88"},
                   "steps": [{"range": [0, 60], "color": "#1a4a8a"},
                              {"range": [60, 85], "color": "#ffa500"},
                              {"range": [85, 100], "color": "#ff4444"}]},
        ))
        fig_mem.update_layout(paper_bgcolor="#16213e", font_color="white", height=250)
        st.plotly_chart(fig_mem, use_container_width=True)

    with col2:
        st.markdown("#### Request Metrics (Last 60 min)")
        time_series = metrics_collector.get_request_timeseries(points=60)
        df_ts = pd.DataFrame(time_series)

        fig_req = px.area(df_ts, x="timestamp", y="requests_per_min",
                          title="Requests / Minute",
                          color_discrete_sequence=["#e94560"])
        fig_req.update_layout(paper_bgcolor="#16213e", plot_bgcolor="#0f3460",
                               font_color="white", showlegend=False)
        st.plotly_chart(fig_req, use_container_width=True)

        fig_lat = px.line(df_ts, x="timestamp", y="p95_latency_ms",
                          title="P95 Latency (ms)",
                          color_discrete_sequence=["#00ff88"])
        fig_lat.update_layout(paper_bgcolor="#16213e", plot_bgcolor="#0f3460",
                               font_color="white", showlegend=False)
        st.plotly_chart(fig_lat, use_container_width=True)

    # Alerts
    st.markdown("#### 🔔 Active Alerts")
    alerts = metrics_collector.get_alerts()
    for alert in alerts:
        if alert["severity"] == "critical":
            st.error(f"🔴 CRITICAL: {alert['message']}")
        elif alert["severity"] == "warning":
            st.warning(f"🟡 WARNING: {alert['message']}")
        else:
            st.success(f"🟢 OK: {alert['message']}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 3 — AWS Deployment
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab3:
    st.subheader("☁️ AWS ECS Deployment Pipeline")

    col1, col2, col3 = st.columns(3)
    col1.metric("ECS Tasks Running", "3/3", "healthy")
    col2.metric("ECR Image Size", "2.1 GB", "-0.3 GB")
    col3.metric("Deploy Time", "4m 32s", "-48s")
    st.caption("Illustrative values for the demonstration; not read from a live AWS account.")

    st.markdown("---")

    if enable_aws and st.button("🚀 Simulate AWS ECS deployment", type="primary", use_container_width=True):
        stages = [
            ("🐳 Building Docker image", 2.0),
            ("📋 Running tests", 1.5),
            ("🔐 Authenticating with ECR", 1.0),
            ("📤 Pushing image to ECR", 2.5),
            ("📝 Updating ECS task definition", 1.0),
            ("🚀 Deploying to ECS cluster", 2.0),
            ("⏳ Waiting for service stability", 1.5),
            ("🏥 Running health checks", 1.0),
            ("✅ Simulated deployment complete (no AWS resources created)", 0.5),
        ]

        progress = st.progress(0)
        status_box = st.empty()
        log_box = st.empty()
        deploy_logs = []

        for i, (stage, duration) in enumerate(stages):
            pct = int(((i + 1) / len(stages)) * 100)
            status_box.markdown(f"**{stage}**")
            progress.progress(pct)

            log_line = f"[{datetime.now().strftime('%H:%M:%S')}] {stage}"
            deploy_logs.append(log_line)
            log_box.code("\n".join(deploy_logs))
            time.sleep(duration)

        st.balloons()
        st.success("✅ Simulated ECS deployment complete. No AWS resources were created.")
        st.json({
            "cluster": "ai-portfolio-cluster",
            "service": "module-3-mlops",
            "task_definition": "module3:42",
            "running_count": 3,
            "image": "<aws-account-id>.dkr.ecr.us-east-1.amazonaws.com/ai-portfolio:latest",
            "load_balancer": "https://example.invalid/module3",
            "deployed_at": datetime.now().isoformat(),
            "status": "ACTIVE (simulated)",
            "simulated": True
        })

    # Architecture diagram
    st.markdown("#### 🏗️ AWS Architecture")
    st.markdown("""
    ```
    Developer Push
         │
         ▼
    ┌─────────────┐    ┌──────────────┐    ┌─────────────────┐
    │   GitHub    │───▶│  CodePipeline│───▶│   CodeBuild     │
    │  (trigger)  │    │  (orchestrate)│   │  (docker build) │
    └─────────────┘    └──────────────┘    └────────┬────────┘
                                                    │
                                                    ▼
                                           ┌─────────────────┐
                                           │   Amazon ECR    │
                                           │  (image store)  │
                                           └────────┬────────┘
                                                    │
                                                    ▼
                                           ┌─────────────────┐
                                           │   Amazon ECS    │◀── ALB ──▶ Users
                                           │  (Fargate tasks)│
                                           └────────┬────────┘
                                                    │
                                           ┌────────┴────────┐
                                           │   CloudWatch    │
                                           │  + Prometheus   │
                                           └─────────────────┘
    ```
    """)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 4 — CI/CD Pipeline
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab4:
    st.subheader("🔁 CI/CD Pipeline Status")

    pipelines = [
        {"name": "module-1-ai-agents", "branch": "main", "status": "✅ PASSED", "duration": "3m 12s", "commit": "a1b2c3d"},
        {"name": "module-2-multi-agent", "branch": "main", "status": "✅ PASSED", "duration": "4m 48s", "commit": "e4f5g6h"},
        {"name": "module-3-mlops", "branch": "feature/monitoring", "status": "🔄 RUNNING", "duration": "2m 01s", "commit": "i7j8k9l"},
    ]
    st.dataframe(pd.DataFrame(pipelines), use_container_width=True)

    st.markdown("#### 📋 GitHub Actions Workflow Preview")
    st.code("""
name: MLOps CI/CD Pipeline

on:
  push:
    branches: [main, feature/*]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with: { python-version: "3.11" }
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest tests/ -v --tb=short
      - name: MLflow smoke test
        run: python tests/test_mlflow_tracking.py

  build-and-push:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      - name: Login to Amazon ECR
        uses: aws-actions/amazon-ecr-login@v2
      - name: Build and push Docker image
        run: |
          docker build -t $ECR_REPO:$GITHUB_SHA .
          docker push $ECR_REPO:$GITHUB_SHA
          docker tag $ECR_REPO:$GITHUB_SHA $ECR_REPO:latest
          docker push $ECR_REPO:latest

  deploy:
    needs: build-and-push
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to ECS
        uses: aws-actions/amazon-ecs-deploy-task-definition@v1
        with:
          task-definition: task-definition.json
          service: module-3-mlops
          cluster: ai-portfolio-cluster
          wait-for-service-stability: true
""", language="yaml")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 5 — Portfolio Stats
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab5:
    st.subheader("📈 AI Engineering Portfolio — Geoffrey Jones Okwi")

    modules = pd.DataFrame([
        {"Module": "1 — Single ReAct Agent", "Status": "✅ LIVE", "Tech": "LangGraph · Groq · Streamlit", "Complexity": 85},
        {"Module": "2 — Multi-Agent System", "Status": "✅ LIVE", "Tech": "Supervisor · RAG · FAISS · DuckDuckGo", "Complexity": 92},
        {"Module": "3 — MLOps Pipeline", "Status": "🔨 Demo", "Tech": "MLflow · Prometheus · Docker · AWS ECS", "Complexity": 97},
    ])
    st.dataframe(modules, use_container_width=True, hide_index=True)

    fig_comp = px.bar(modules, x="Module", y="Complexity",
                      title="Portfolio Complexity Score",
                      color="Complexity", color_continuous_scale="reds",
                      text="Complexity")
    fig_comp.update_layout(paper_bgcolor="#16213e", plot_bgcolor="#0f3460",
                            font_color="white")
    st.plotly_chart(fig_comp, use_container_width=True)

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        ### 🎯 Skills Demonstrated
        - **LangGraph** — Multi-agent orchestration
        - **Groq** — Ultra-fast LLM inference
        - **MLflow** — Experiment tracking & model registry
        - **Prometheus** — Metrics and monitoring setup
        - **Docker** — Containerization
        - **AWS ECS/ECR** — Deployment workflow (simulated)
        - **GitHub Actions** — CI/CD workflow design
        - **FAISS + HuggingFace** — Vector search / RAG
        """)
    with col2:
        st.markdown("""
        ### 💼 Target Roles
        - Senior AI/ML Engineer 
        - MLOps Engineer 
        - AI Platform Engineer 
        - Staff AI Engineer 

        ### 📚 Training
        - Stanford / Andrew Ng AI, ML and deep learning course materials
        - Commander Smart Eagle program
        - 3-module AI engineering portfolio
        """)