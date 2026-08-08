import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data.minerals_data import MINERALS, get_categories, get_mineral_by_symbol
from sim.analytics import compute_hhi, hhi_band, concentration_risk_score, dominant_supplier
from sim.disruption_sim import DisruptionSimulation
from rag.qa_engine import BastionQA

st.set_page_config(page_title="Bastion — Critical Minerals Supply Chain", layout="wide")

st.title("🛡️ Bastion — Critical Minerals Supply Chain Module")
st.caption(
    "Module 9 · AI Engineering Portfolio · Physical/chemical properties, "
    "supply concentration, and discrete-event disruption simulation."
)

tab1, tab2, tab3, tab4 = st.tabs(
    ["🔬 Mineral Explorer", "🌍 Supply Concentration", "⚡ Disruption Simulator", "💬 Ask Bastion"]
)

# ---------------------------------------------------------------------
# TAB 1 — Mineral Explorer
# ---------------------------------------------------------------------
with tab1:
    st.subheader("Mineral Explorer")

    categories = ["All"] + get_categories()
    col_a, col_b = st.columns([1, 3])
    with col_a:
        selected_category = st.selectbox("Filter by category", categories)

    filtered = MINERALS if selected_category == "All" else [
        m for m in MINERALS if m["category"] == selected_category
    ]

    all_applications = sorted({app for m in MINERALS for app in m["applications"]})
    with col_b:
        selected_apps = st.multiselect("Filter by application", all_applications)
    if selected_apps:
        filtered = [m for m in filtered if any(a in m["applications"] for a in selected_apps)]

    st.markdown(f"**{len(filtered)} minerals match**")

    cols = st.columns(3)
    for i, m in enumerate(filtered):
        with cols[i % 3]:
            with st.container(border=True):
                st.markdown(f"### {m['symbol']} — {m['name']}")
                st.caption(m["category"])
                pp = m["physical_properties"]
                cp = m["chemical_properties"]
                st.markdown(
                    f"**Physical:** {pp['color']}, density {pp['density_g_cm3']} g/cm³, "
                    f"melts at {pp['melting_point_c']} °C"
                )
                st.markdown(f"**Chemical:** {cp['formula']} — {cp['reactivity']}")
                st.markdown(f"**Applications:** {', '.join(m['applications'])}")
                country, share = dominant_supplier(m)
                source_tag = "✅ USGS MCS 2025" if m.get("data_source") == "MCS2025" else "〰 Estimate"
                st.markdown(f"**Dominant supplier:** {country} ({share*100:.0f}%) · {source_tag}")

# ---------------------------------------------------------------------
# TAB 2 — Supply Concentration
# ---------------------------------------------------------------------
with tab2:
    st.subheader("Supply Concentration & Criticality")
    st.caption(
        "Nd, Dy, Ga, Co, and Li figures are sourced directly from USGS Mineral "
        "Commodity Summaries 2025 (2024 production data). Remaining minerals use "
        "industry-consensus estimates not individually re-verified this pass. "
        "See the Data Source column below. HHI computed on the standard 0–10,000 scale."
    )

    rows = []
    for m in MINERALS:
        hhi = compute_hhi(m["producing_countries"])
        country, share = dominant_supplier(m)
        rows.append({
            "Symbol": m["symbol"],
            "Mineral": m["name"],
            "Category": m["category"],
            "HHI": round(hhi),
            "Concentration": hhi_band(hhi),
            "Dominant Supplier": country,
            "Dominant Share %": round(share * 100, 1),
            "Substitutability": m["substitutability"],
            "Risk Score": concentration_risk_score(m),
            "Data Source": "USGS MCS 2025" if m.get("data_source") == "MCS2025" else "Estimate",
        })
    df = pd.DataFrame(rows).sort_values("Risk Score", ascending=False)

    col1, col2 = st.columns([2, 1])
    with col1:
        fig = px.bar(
            df, x="Mineral", y="Risk Score", color="Concentration",
            color_discrete_map={
                "High concentration": "#c0392b",
                "Moderate concentration": "#d68910",
                "Competitive": "#1e8449",
            },
            hover_data=["Dominant Supplier", "Dominant Share %", "HHI"],
            title="Supply Chain Risk Score by Mineral",
        )
        fig.update_layout(xaxis_tickangle=-45, height=450)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("#### Highest-risk minerals")
        for _, r in df.head(5).iterrows():
            st.markdown(
                f"**{r['Mineral']}** — {r['Dominant Supplier']} "
                f"({r['Dominant Share %']}%) · Risk {r['Risk Score']}"
            )

    st.markdown("#### Full concentration table")
    st.dataframe(df, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------
# TAB 3 — Disruption Simulator
# ---------------------------------------------------------------------
with tab3:
    st.subheader("Disruption Simulator")
    st.caption(
        "Discrete-event simulation (SimPy). Choose a mineral, a source country to "
        "disrupt, and severity. Recovery-time ranges are loosely informed by "
        "historical analogues but are illustrative, not calibrated forecasts."
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        mineral_symbol = st.selectbox(
            "Mineral", [m["symbol"] for m in MINERALS],
            format_func=lambda s: f"{s} — {get_mineral_by_symbol(s)['name']}",
        )
    mineral = get_mineral_by_symbol(mineral_symbol)

    with col2:
        source_country = st.selectbox(
            "Disrupted source country", list(mineral["producing_countries"].keys())
        )
    with col3:
        severity = st.selectbox("Severity", ["Low", "Moderate", "Severe"], index=1)
    with col4:
        horizon = st.slider("Horizon (days)", 90, 720, 540, step=30)

    run = st.button("▶ Run simulation", type="primary")

    if run:
        sim = DisruptionSimulation(
            mineral=mineral, source_country=source_country,
            severity=severity, horizon_days=horizon,
        )
        timeline = sim.run()
        summary = sim.summary()
        sector_timelines = sim.sector_impact_timeline()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Initial supply drop", f"{summary['initial_drop_pct']}%")
        c2.metric("Trough availability", f"{summary['trough_availability_pct']}%",
                   delta=f"day {summary['trough_day']}", delta_color="off")
        c3.metric("Est. recovery time", f"{summary['estimated_recovery_days']} days")
        c4.metric("Sectors affected", len(mineral["applications"]))

        tdf = pd.DataFrame(timeline)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=tdf["day"], y=tdf["mineral_availability_pct"],
            mode="lines", name=f"{mineral['name']} supply availability",
            line=dict(color="#c0392b", width=3),
        ))
        for app, series in sector_timelines.items():
            sdf = pd.DataFrame(series)
            fig.add_trace(go.Scatter(
                x=sdf["day"], y=sdf["sector_availability_pct"],
                mode="lines", name=app, line=dict(dash="dot"), opacity=0.7,
            ))
        fig.update_layout(
            title=f"Cascade: {source_country} disruption of {mineral['name']} ({severity})",
            xaxis_title="Days since disruption",
            yaxis_title="Availability (% of normal)",
            height=500,
        )
        st.plotly_chart(fig, use_container_width=True)

        st.info(
            f"A **{severity.lower()}** disruption at **{source_country}** "
            f"(supplies {mineral['producing_countries'][source_country]*100:.0f}% of global "
            f"{mineral['name']}) drops availability by an estimated "
            f"**{summary['initial_drop_pct']}%**, with recovery to baseline in "
            f"roughly **{summary['estimated_recovery_days']} days**. "
            f"Downstream sectors — {', '.join(mineral['applications'])} — inherit this "
            f"shortfall proportionally to assumed dependency weight."
        )
    else:
        st.markdown("Configure a scenario above and run the simulation.")

# ---------------------------------------------------------------------
# TAB 4 — Ask Bastion (Hybrid RAG Query Assistant)
# ---------------------------------------------------------------------
with tab4:
    st.subheader("Ask Bastion")
    st.caption(
        "Hybrid RAG query assistant — TF-IDF/cosine + keyword hybrid scoring "
        "over the Bastion dataset, answers via Groq (llama-3.3-70b-versatile), "
        "with conversational memory and source transparency. "
        "e.g. \"What critical mineral is used in lasers?\" or "
        "\"Which minerals does China dominate supply of?\""
    )

    @st.cache_resource
    def _get_qa_engine():
        return BastionQA(MINERALS, alpha=0.6, top_k=4)

    qa = _get_qa_engine()

    if qa.client is None:
        st.warning(
            "GROQ_API_KEY not found in environment — running in retrieval-only "
            "fallback mode (no LLM-generated answers). Set GROQ_API_KEY in "
            "Streamlit Cloud secrets to enable full RAG responses.",
            icon="⚠️",
        )

    if "bastion_chat_history" not in st.session_state:
        st.session_state.bastion_chat_history = []

    for msg in st.session_state.bastion_chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("sources"):
                st.caption("Sources: " + ", ".join(msg["sources"]))

    query = st.chat_input("Ask about a critical mineral, application, or supply risk...")
    if query:
        st.session_state.bastion_chat_history.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)

        history_for_llm = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.bastion_chat_history
            if m["role"] in ("user", "assistant")
        ]

        with st.chat_message("assistant"):
            with st.spinner("Retrieving and reasoning..."):
                result = qa.answer(query, history=history_for_llm[:-1])
            st.markdown(result["answer"])
            if result["sources"]:
                st.caption("Sources: " + ", ".join(result["sources"]))

        st.session_state.bastion_chat_history.append({
            "role": "assistant",
            "content": result["answer"],
            "sources": result["sources"],
        })

    if st.session_state.bastion_chat_history:
        if st.button("Clear conversation"):
            st.session_state.bastion_chat_history = []
            st.rerun()

st.divider()
st.caption(
    "Bastion — Module 9, AI Engineering Portfolio. Reference data is illustrative "
    "and not sourced from a live feed. Not investment, procurement, or policy advice."
)