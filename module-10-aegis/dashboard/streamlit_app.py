"""
AEGIS — Streamlit Dashboard
Module 10, ai-engineering-portfolio

Four panels:
  1. Overview — scenario summary, risk tier distribution, detection metrics
  2. Transaction Graph — interactive network view of flagged wallets and their connections
  3. Escalation Queue — human-in-the-loop case review, wired directly to
     AuthorityBoundary (Tier 3 enforcement actions only unlock after a
     recorded adjudication, exactly as the governance layer requires)
  4. Explainability — ensemble feature importances + per-wallet score breakdown

Run: streamlit run dashboard/streamlit_app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running via `streamlit run dashboard/streamlit_app.py` from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import networkx as nx
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.ingestion.transaction_simulator import SimulatorConfig, TransactionSimulator
from src.scoring.ensemble_classifier import assemble_features, train_and_validate
from src.scoring.sanctions_matcher import build_synthetic_watchlist, screen_wallets
from src.scoring.composite_score import compute_composite_score
from src.features.mixer_proximity import designate_mixer_wallets
from src.features.graph_centrality import build_transaction_graph
from src.governance.authority_boundary import (
    AuthorityBoundary,
    AdjudicationRecord,
    AuthorityBoundaryViolation,
)

st.set_page_config(page_title="AEGIS — On-Chain AML Detection", layout="wide", page_icon="🛡️")

ESCALATION_THRESHOLD = 0.6


# ---------------------------------------------------------------------
# Cross-version compatibility shim.
#
# Streamlit's `width='stretch'` API (replacing `use_container_width`)
# was only added in ~1.5x+; the exact version cutoff differs per
# element (plotly_chart vs dataframe), and different deployment targets
# (local .venv, Streamlit Cloud) can end up on different installed
# versions even with the same requirements.txt pin -- e.g. if Cloud's
# build cache hasn't picked up a requirements.txt change yet. Rather
# than depend on every environment matching exactly, these wrappers try
# the modern API first and fall back to the older one on TypeError, so
# the dashboard renders correctly regardless of which Streamlit version
# actually ends up installed.
# ---------------------------------------------------------------------
def _plotly_chart(fig):
    try:
        st.plotly_chart(fig, width="stretch")
    except TypeError:
        st.plotly_chart(fig, use_container_width=True)


def _dataframe(data):
    try:
        st.dataframe(data, width="stretch")
    except TypeError:
        st.dataframe(data, use_container_width=True)


# ---------------------------------------------------------------------
# Cached pipeline run — regenerating on every widget interaction would
# retrain the ensemble each time, so the full pipeline is cached and
# only the human-adjudication step happens live via session_state.
# ---------------------------------------------------------------------
@st.cache_resource(show_spinner="Running AEGIS pipeline: generating ledger, training ensemble, scoring...")
def run_pipeline(seed: int):
    config = SimulatorConfig(seed=seed)
    sim = TransactionSimulator(config)
    ledger = sim.run()

    features = assemble_features(ledger)
    clf, metrics = train_and_validate(features)

    full_scores = clf.predict_proba(features)
    full_scores.index = features["wallet"].values

    watchlist = build_synthetic_watchlist(ledger, seed=seed + 1000)
    mixers = set(designate_mixer_wallets(ledger, seed=seed))
    screening = screen_wallets(ledger, watchlist, mixers)

    composite = compute_composite_score(full_scores, screening)
    composite = composite.merge(
        features[["wallet", "is_laundering"]], on="wallet", how="left"
    )

    graph = build_transaction_graph(ledger)
    importances = clf.feature_importances()

    return ledger, features, composite, graph, importances, metrics, mixers, watchlist


def get_boundary() -> AuthorityBoundary:
    if "boundary" not in st.session_state:
        st.session_state.boundary = AuthorityBoundary()
    return st.session_state.boundary


def get_escalated_case_ids() -> set:
    if "escalated_case_ids" not in st.session_state:
        st.session_state.escalated_case_ids = set()
    return st.session_state.escalated_case_ids


# ---------------------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------------------
st.sidebar.title("🛡️ AEGIS")
st.sidebar.caption("On-Chain Fraud & AML Detection Engine — Module 10")
seed = st.sidebar.number_input("Scenario seed", min_value=1, max_value=9999, value=42, step=1)
st.sidebar.divider()
st.sidebar.markdown(
    "**Governance:** Tier 0–2 (ingest, score, escalate) run autonomously. "
    "Tier 3 (freeze / SAR / regulator notice) is hard-gated behind human "
    "adjudication — see the Escalation Queue tab."
)

ledger, features, composite, graph, importances, metrics, mixers, watchlist = run_pipeline(seed)
boundary = get_boundary()

# Auto-populate the escalation queue for this scenario (Tier 0-2, autonomous)
escalated_ids = get_escalated_case_ids()
if not escalated_ids:
    for _, row in composite.sort_values("composite_score", ascending=False).iterrows():
        if row["composite_score"] >= ESCALATION_THRESHOLD:
            case = boundary.escalate(
                wallet=row["wallet"],
                composite_score=row["composite_score"],
                risk_tier=row["risk_tier"],
                evidence={
                    "ml_score": round(row["ml_score"], 3),
                    "sanctions_rule_score": row["sanctions_rule_score"],
                },
            )
            escalated_ids.add(case.case_id)

tab_overview, tab_graph, tab_queue, tab_explain = st.tabs(
    ["📊 Overview", "🕸️ Transaction Graph", "📋 Escalation Queue", "🔍 Explainability"]
)

# ---------------------------------------------------------------------
# TAB 1: Overview
# ---------------------------------------------------------------------
with tab_overview:
    st.subheader("Scenario Summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Transactions", f"{len(ledger):,}")
    c2.metric("Wallets Scored", f"{len(features):,}")
    c3.metric("Ensemble ROC-AUC", f"{metrics['auc']:.4f}")
    c4.metric("Escalations", f"{len(escalated_ids)}")

    st.divider()
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown("**Risk Tier Distribution**")
        tier_counts = composite["risk_tier"].value_counts().reindex(
            ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        ).fillna(0)
        tier_colors = {"CRITICAL": "#c0392b", "HIGH": "#e67e22", "MEDIUM": "#f1c40f", "LOW": "#27ae60"}
        fig = go.Figure(
            go.Bar(
                x=tier_counts.index,
                y=tier_counts.values,
                marker_color=[tier_colors[t] for t in tier_counts.index],
            )
        )
        fig.update_layout(height=320, margin=dict(t=10, b=10, l=10, r=10))
        _plotly_chart(fig)

    with col_right:
        st.markdown("**Composite Score Separation (Ground Truth)**")
        fig2 = go.Figure()
        for label, name, color in [(True, "Laundering", "#c0392b"), (False, "Clean", "#27ae60")]:
            subset = composite[composite["is_laundering"] == label]["composite_score"]
            fig2.add_trace(go.Box(y=subset, name=name, marker_color=color))
        fig2.update_layout(height=320, margin=dict(t=10, b=10, l=10, r=10))
        _plotly_chart(fig2)

    st.caption(
        "Composite score = 0.7 × ensemble ML probability + 0.3 × sanctions rule score, "
        "with a rule-floor guarantee: any direct watchlist hit forces composite_score = 1.0 "
        "regardless of the ML component."
    )

# ---------------------------------------------------------------------
# TAB 2: Transaction Graph
# ---------------------------------------------------------------------
with tab_graph:
    st.subheader("Transaction Network — Flagged Wallets")
    top_n = st.slider("Show top N highest-risk wallets and their direct counterparties", 5, 50, 20)

    top_wallets = composite.sort_values("composite_score", ascending=False).head(top_n)["wallet"].tolist()
    subgraph_nodes = set(top_wallets)
    for w in top_wallets:
        if w in graph:
            subgraph_nodes.update(graph.predecessors(w))
            subgraph_nodes.update(graph.successors(w))

    subgraph = graph.subgraph(subgraph_nodes)
    pos = nx.spring_layout(subgraph, seed=42, k=0.6)

    score_lookup = composite.set_index("wallet")["composite_score"].to_dict()
    tier_lookup = composite.set_index("wallet")["risk_tier"].to_dict()
    tier_color_map = {"CRITICAL": "#c0392b", "HIGH": "#e67e22", "MEDIUM": "#f1c40f", "LOW": "#95a5a6"}

    edge_x, edge_y = [], []
    for src, dst in subgraph.edges():
        x0, y0 = pos[src]
        x1, y1 = pos[dst]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]
    edge_trace = go.Scatter(x=edge_x, y=edge_y, mode="lines", line=dict(width=0.5, color="#888"), hoverinfo="none")

    node_x, node_y, node_color, node_text, node_size = [], [], [], [], []
    for node in subgraph.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        tier = tier_lookup.get(node, "LOW")
        node_color.append(tier_color_map.get(tier, "#95a5a6"))
        score = score_lookup.get(node, 0.0)
        node_text.append(f"{node}<br>Score: {score:.3f}<br>Tier: {tier}")
        node_size.append(8 + 20 * score)

    node_trace = go.Scatter(
        x=node_x, y=node_y, mode="markers", hoverinfo="text", text=node_text,
        marker=dict(size=node_size, color=node_color, line=dict(width=1, color="#333")),
    )

    fig3 = go.Figure(data=[edge_trace, node_trace])
    fig3.update_layout(
        height=600, showlegend=False, margin=dict(t=10, b=10, l=10, r=10),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
    )
    _plotly_chart(fig3)
    st.caption("Node size and color scale with composite risk score. Red = CRITICAL, orange = HIGH, yellow = MEDIUM, grey = LOW.")

# ---------------------------------------------------------------------
# TAB 3: Escalation Queue (governance-wired)
# ---------------------------------------------------------------------
with tab_queue:
    st.subheader("Escalation Queue — Human Adjudication Required for Enforcement")
    st.info(
        "AEGIS cannot freeze wallets, file SARs, or notify regulators autonomously. "
        "Every enforcement action below requires a recorded adjudication first — "
        "this is enforced in code (`AuthorityBoundary.request_enforcement`), not just policy.",
        icon="🔒",
    )

    pending = boundary.pending_cases()
    if not pending:
        st.success("No pending cases. All escalations have been adjudicated.")
    else:
        for case in sorted(pending, key=lambda c: c.composite_score, reverse=True):
            with st.expander(
                f"{case.wallet}  —  {case.risk_tier}  —  score {case.composite_score:.3f}"
            ):
                st.json(case.evidence)
                col_a, col_b, col_c = st.columns([2, 1, 1])
                reviewer = col_a.text_input("Reviewer ID", value="analyst_jsh", key=f"rev_{case.case_id}")
                justification = st.text_area("Justification", key=f"just_{case.case_id}")

                b1, b2 = st.columns(2)
                if b1.button("✅ Confirm — Authorize Enforcement", key=f"confirm_{case.case_id}"):
                    boundary.record_adjudication(
                        AdjudicationRecord(case.case_id, reviewer, "confirmed", justification or "No justification provided.")
                    )
                    result = boundary.request_enforcement(case.case_id, "freeze_wallet")
                    st.success(f"Enforcement authorized and logged: {result['action']} by {result['authorized_by']}")
                    st.rerun()
                if b2.button("❌ Clear — False Positive", key=f"clear_{case.case_id}"):
                    boundary.record_adjudication(
                        AdjudicationRecord(case.case_id, reviewer, "cleared", justification or "No justification provided.")
                    )
                    st.info("Case cleared. No enforcement action taken or possible for this case.")
                    st.rerun()

    log = boundary.enforcement_log()
    if log:
        st.divider()
        st.markdown("**Enforcement Log** (only reachable via confirmed adjudication)")
        _dataframe(pd.DataFrame(log))

    # Demonstrate the hard gate explicitly
    st.divider()
    with st.expander("🔒 Governance boundary self-test (blocked-path demonstration)"):
        st.write(
            "Attempting a Tier 3 action on a case with no adjudication record raises "
            "`AuthorityBoundaryViolation` — there is no bypass parameter."
        )
        if pending:
            demo_case = pending[0]
            try:
                boundary.request_enforcement(demo_case.case_id, "freeze_wallet")
                st.error("This should not have succeeded.")
            except AuthorityBoundaryViolation as e:
                st.code(str(e), language=None)
        else:
            st.write("No pending cases available to demonstrate against right now.")

# ---------------------------------------------------------------------
# TAB 4: Explainability
# ---------------------------------------------------------------------
with tab_explain:
    st.subheader("Ensemble Feature Importances")
    imp_df = importances.reset_index()
    imp_df.columns = ["feature", "importance"]
    fig4 = go.Figure(go.Bar(x=imp_df["importance"], y=imp_df["feature"], orientation="h"))
    fig4.update_layout(height=450, margin=dict(t=10, b=10, l=10, r=10), yaxis=dict(autorange="reversed"))
    _plotly_chart(fig4)

    st.divider()
    st.subheader("Per-Wallet Score Breakdown")
    selected_wallet = st.selectbox(
        "Select a wallet to inspect",
        composite.sort_values("composite_score", ascending=False)["wallet"].head(50).tolist(),
    )
    row = composite[composite["wallet"] == selected_wallet].iloc[0]
    feat_row = features[features["wallet"] == selected_wallet].iloc[0]

    c1, c2, c3 = st.columns(3)
    c1.metric("ML Score", f"{row['ml_score']:.3f}")
    c2.metric("Sanctions Rule Score", f"{row['sanctions_rule_score']:.3f}")
    c3.metric("Composite Score", f"{row['composite_score']:.3f}", delta=row["risk_tier"])

    st.markdown("**Underlying feature values for this wallet**")
    _dataframe(feat_row.to_frame().T)

    st.caption(
        "Note: this panel shows global feature importances plus the wallet's raw feature "
        "values, not a formal per-prediction attribution (e.g. SHAP). That would be the "
        "natural next iteration for a production version of this dashboard."
    )