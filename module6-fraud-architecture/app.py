"""
app.py — Module 6: Sentry Architecture Dashboard

Scope note: this dashboard visualizes exactly what has been built and proven —
ADR-001 through ADR-006 and the 14 validated simulation scenarios in
sim/sentry_sim.py. It does not include tabs for anything not yet backed by
an ADR, to keep this dashboard an honest reflection of the module's actual
state (same discipline as Module 5).

Run locally:
    streamlit run app.py
"""

import io
import contextlib
from pathlib import Path

import streamlit as st

from sim.sentry_sim import (
    Action,
    Tier2Type,
    TrustCacheEntry,
    IngestionLayer,
    ScoringLayer,
    AuditLayer,
    HumanEscalationLayer,
    DecisionLayer,
    DEFAULT_DECLINE_THRESHOLD,
    DEFAULT_FRICTION_THRESHOLD,
    FAILOPEN_MAX_AMOUNT,
    INGESTION_BUDGET_MS,
    SCORING_BUDGET_MS,
    run_all,
)

BASE_DIR = Path(__file__).parent
ADR_DIR = BASE_DIR / "adr"

st.set_page_config(
    page_title="Module 6: Sentry Architecture",
    page_icon="🛡️",
    layout="wide",
)

ACTION_COLORS = {
    Action.APPROVE: "#2e7d32",
    Action.HOLD_FOR_REVIEW: "#f9a825",
    Action.DECLINE: "#ef6c00",
    Action.ESCALATE_TIER2: "#c62828",
}


def action_badge(action: Action) -> str:
    color = ACTION_COLORS[action]
    return (
        f"<span style='background-color:{color};color:white;padding:4px 12px;"
        f"border-radius:12px;font-weight:600;font-size:0.9rem'>{action.value}</span>"
    )


def mermaid(code: str, height: int = 440) -> None:
    """Render a Mermaid diagram via CDN inside an HTML component."""
    html = f"""
    <div class="mermaid">
    {code}
    </div>
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({{ startOnLoad: true, theme: 'neutral' }});
    </script>
    """
    st.components.v1.html(html, height=height, scrolling=True)


# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------
st.sidebar.title("🛡️ Sentry Architecture")
st.sidebar.caption("Module 6 — AI Engineering Portfolio")
page = st.sidebar.radio(
    "Navigate",
    ["Overview", "System Architecture", "ADR Browser", "Live Simulation", "Test Suite"],
)
st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Scope:** ADR-001 → ADR-006\n\n"
    "**Domain:** Real-time fraud/anomaly detection\n\n"
    "**Focus:** Decision architecture, not a production fraud model"
)
st.sidebar.markdown(
    "[GitHub repo](https://github.com/joneslokouba-ui/ai-engineering-portfolio)"
)

# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------
if page == "Overview":
    st.title("Module 6: Sentry Architecture")
    st.subheader("System Architecture for Real-Time Fraud & Anomaly Detection")

    st.markdown(
        """
This module is not a production fraud model. It is an **architecture decision record (ADR) set**
plus a **discrete-event simulation** proving the hard design decisions behind a real-time
transaction fraud-screening system — where a false positive harms a legitimate customer and a
false negative costs the business, and both directions carry real, distinct consequences.

Module 5 (Sentinel Architecture) proved a system design for AI whose mistakes have *physical*
consequences. This module proves the adjacent skill: designing AI systems whose mistakes have
*financial and legal* consequences.
"""
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("ADRs Written", "6")
    col2.metric("Simulation Scenarios", "14")
    col3.metric("Scenarios Passing", "14 / 14")

    st.markdown("### What's actually proven here")
    st.markdown(
        """
- **ADR-001** — the model never has autonomous authority over irreversible/legal actions (permanent
  suspension, fund freeze, law-enforcement referral) — those are always routed to a human
- **ADR-002** — per-layer latency budgets (ingestion, scoring) with fail-fast behavior
- **ADR-003** — fail-closed by default on timeout, with a narrow, bounded fail-open exception
  for low-amount, trusted, freshly-cached accounts
- **ADR-004** — false positives and false negatives handled via two independently owned,
  independently tunable thresholds, not one accuracy-optimized cutoff
- **ADR-005** — every decision requires a confirmed audit record; if the audit write fails, the
  decision is downgraded to the fail-closed action rather than left unlogged
- **ADR-006** — forensic attribution feedback (fraud-ring clustering) is advisory-only; a
  confirmed cluster can only shift the score through the existing thresholds, and can never
  itself trigger a Tier 2 action

Use the sidebar to explore the architecture diagrams, read the ADRs in full, run the decision
pipeline interactively, or re-run the full 14-scenario test suite.
"""
    )

# ---------------------------------------------------------------------------
# System Architecture
# ---------------------------------------------------------------------------
elif page == "System Architecture":
    st.title("System Architecture")

    st.markdown("#### Layer diagram")
    st.caption(
        "The arrow from Decision → Human Escalation for Tier 2 actions is this module's "
        "equivalent of Module 5's Decision → Control boundary (ADR-001)."
    )
    mermaid(
        """
flowchart TB
    subgraph RealTime["Real-Time Path (latency-critical)"]
        I[Ingestion Layer<br/>event stream, feature extraction]
        S[Scoring Layer<br/>fraud model / ensemble]
        D[Decision Layer<br/>thresholding: approve / decline / hold]
    end
    subgraph Oversight["Human Oversight"]
        H[Human Escalation Layer<br/>review queue, SLA-bound]
    end
    A[Audit / Compliance Layer<br/>immutable decision log]
    I --> S --> D
    D -->|"Tier 1: reversible (autonomous)"| Outcome[Approve / Decline / Hold]
    D -->|"Tier 2: irreversible or legal (recommend only)"| H
    D -.->|every decision logged| A
    H -.->|escalation outcomes logged| A
    style D fill:#f9a825,color:#000
    style H fill:#c62828,color:#fff
    style S fill:#0288d1,color:#fff
    style I fill:#5bc0de,color:#000
    style A fill:#2e7d32,color:#fff
""",
        height=440,
    )

    st.markdown("#### Failure scenario: scoring timeout → bounded fail-open decision")
    mermaid(
        """
sequenceDiagram
    participant FeatureStore as Feature Store
    participant Ingestion as Ingestion Layer
    participant Scoring as Scoring Layer
    participant Decision as Decision Layer

    FeatureStore->>Ingestion: feature lookup
    Note over Scoring: scoring timeout (>100ms)
    Scoring->>Decision: SCORE_TIMEOUT flag
    Decision->>Decision: check amount + trust cache
    alt amount < $25 AND trusted AND fresh
        Decision->>Decision: APPROVE (bounded fail-open exception)
    else
        Decision->>Decision: HOLD_FOR_REVIEW (fail-closed default)
    end
    Decision->>Decision: write audit record (ADR-005)
    alt audit write fails
        Decision->>Decision: downgrade to HOLD_FOR_REVIEW
    end
""",
        height=420,
    )

# ---------------------------------------------------------------------------
# ADR Browser
# ---------------------------------------------------------------------------
elif page == "ADR Browser":
    st.title("Architecture Decision Records")

    adr_files = sorted(ADR_DIR.glob("ADR-0*.md"))
    if not adr_files:
        st.error("No ADR files found. Expected them under adr/ relative to this app.")
    else:
        labels = [f.stem for f in adr_files]
        choice = st.selectbox("Select an ADR", labels, index=0)
        selected_path = ADR_DIR / f"{choice}.md"
        st.markdown(selected_path.read_text(encoding="utf-8"))

# ---------------------------------------------------------------------------
# Live Simulation
# ---------------------------------------------------------------------------
elif page == "Live Simulation":
    st.title("Live Simulation")
    st.caption(
        "Drive the Ingestion, Scoring, and Audit layers yourself and watch the Decision layer "
        "enforce the ADR-001 through ADR-006 boundaries in real time."
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### Pipeline timing")
        ingestion_latency = st.slider(
            "Ingestion latency (ms)", 0, 300, 40, help=f"Budget is {INGESTION_BUDGET_MS}ms (ADR-002)"
        )
        scoring_latency = st.slider(
            "Scoring latency (ms)", 0, 200, 60, help=f"Budget is {SCORING_BUDGET_MS}ms (ADR-002)"
        )
        score = st.slider("Fraud score (0-1)", 0.0, 1.0, 0.10, 0.01, help="Only used if neither layer times out")
    with col2:
        st.markdown("##### Transaction context")
        amount = st.number_input("Transaction amount ($)", value=80.0, min_value=0.0)
        trusted = st.checkbox("Account trusted (good standing)", value=True)
        fresh = st.checkbox("Trust cache entry is fresh", value=True)
        audit_force_fail = st.checkbox("Simulate audit-write failure (tests ADR-005)")

    st.markdown("##### Threshold configuration (ADR-004)")
    c1, c2 = st.columns(2)
    with c1:
        decline_threshold = st.slider("Decline threshold", 0.0, 1.0, DEFAULT_DECLINE_THRESHOLD, 0.05)
    with c2:
        friction_threshold = st.slider("Friction threshold", 0.0, 1.0, DEFAULT_FRICTION_THRESHOLD, 0.05)

    st.markdown("##### Adversarial Tier 2 injection (tests ADR-001)")
    inject_tier2 = st.checkbox("Force a Tier 2 action request from the Decision layer")
    forced_tier2 = None
    if inject_tier2:
        tier2_choice = st.selectbox("Tier 2 action to request", [t.name for t in Tier2Type])
        forced_tier2 = Tier2Type[tier2_choice]

    if st.button("Run through the pipeline", type="primary"):
        ingestion = IngestionLayer().extract(latency_ms=ingestion_latency)
        scoring = ScoringLayer().score_transaction(latency_ms=scoring_latency, score=score)
        audit = AuditLayer()
        escalation = HumanEscalationLayer()
        decision = DecisionLayer(decline_threshold=decline_threshold, friction_threshold=friction_threshold)

        record = decision.decide(
            ingestion, scoring, amount=amount,
            trust=TrustCacheEntry(trusted=trusted, fresh=fresh),
            audit=audit, escalation=escalation,
            audit_force_fail=audit_force_fail,
            forced_tier2_request=forced_tier2,
        )

        st.markdown("---")
        r1, r2, r3 = st.columns(3)
        with r1:
            st.markdown("**Ingestion / Scoring status**")
            st.markdown(
                f"Ingestion: {'⏱️ TIMEOUT' if ingestion.timed_out else '✅ on time'}  \n"
                f"Scoring: {'⏱️ TIMEOUT' if scoring.timed_out else '✅ on time'}"
            )
        with r2:
            st.markdown("**Final action**")
            st.markdown(action_badge(record.action), unsafe_allow_html=True)
        with r3:
            st.markdown("**Score used**")
            st.markdown(f"{record.score:.2f}" if record.score is not None else "n/a (timeout path)")

        st.info(f"**Reason:** {record.reason}")

        if escalation.queue:
            st.warning(
                f"⚠️ Tier 2 action **{escalation.queue[0].value}** was requested but NOT auto-executed — "
                f"it was routed to the Human Escalation queue instead. This is ADR-001 in action."
            )

        if audit.records:
            st.success(f"✅ Audit record confirmed and stored ({len(audit.records)} record(s) this run).")
        else:
            st.error("❌ No audit record was confirmed — decision was downgraded per ADR-005.")

# ---------------------------------------------------------------------------
# Test Suite
# ---------------------------------------------------------------------------
elif page == "Test Suite":
    st.title("Test Suite")
    st.caption(
        "Runs the same 14 scenarios from sim/sentry_sim.py that validate ADR-001 through "
        "ADR-006. This is the exact proof, not a reimplementation."
    )

    if st.button("Run all 14 scenarios", type="primary"):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            run_all()
        output = buffer.getvalue()

        lines = [l for l in output.splitlines() if l.startswith("[PASS]") or l.startswith("[FAIL]")]
        passed = sum(1 for l in lines if l.startswith("[PASS]"))
        total = len(lines)

        if passed == total:
            st.success(f"All {total} scenarios passed.")
        else:
            st.error(f"{passed} / {total} scenarios passed — review below.")

        for line in lines:
            if line.startswith("[PASS]"):
                st.markdown(f"✅ {line[7:]}")
            else:
                st.markdown(f"❌ {line[7:]}")

        with st.expander("Raw console output"):
            st.code(output, language="text")