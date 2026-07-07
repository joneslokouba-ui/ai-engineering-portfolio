"""
app.py — Module 5: Sentinel Architecture Dashboard

Scope note: this dashboard visualizes exactly what has been built and proven —
ADR-001 through ADR-004 and the 8 validated simulation scenarios in
sim/failsafe_sim.py. It deliberately does not include tabs for architecture
decisions that haven't been written yet (edge/cloud split, fleet coordination,
OTA updates) — those get added here only once they exist as ADRs, to keep
this dashboard an honest reflection of the current state of the module.

Run locally:
    streamlit run app.py
"""

import io
import contextlib
from pathlib import Path

import streamlit as st

from sim.failsafe_sim import (
    DegradationState,
    IntentType,
    Intent,
    PerceptionLayer,
    PerceptionOutput,
    DecisionLayer,
    ControlLayer,
    run_all,
)

BASE_DIR = Path(__file__).parent
ADR_DIR = BASE_DIR / "adr"

st.set_page_config(
    page_title="Module 5: Sentinel Architecture",
    page_icon="🛸",
    layout="wide",
)

STATE_COLORS = {
    DegradationState.NOMINAL: "#2e7d32",
    DegradationState.DEGRADED: "#f9a825",
    DegradationState.LOST: "#ef6c00",
    DegradationState.FAIL_SAFE: "#c62828",
}


def state_badge(state: DegradationState) -> str:
    color = STATE_COLORS[state]
    return (
        f"<span style='background-color:{color};color:white;padding:4px 12px;"
        f"border-radius:12px;font-weight:600;font-size:0.9rem'>{state.name}</span>"
    )


def mermaid(code: str, height: int = 420) -> None:
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
st.sidebar.title("🛸 Sentinel Architecture")
st.sidebar.caption("Module 5 — AI Engineering Portfolio")
page = st.sidebar.radio(
    "Navigate",
    ["Overview", "System Architecture", "ADR Browser", "Live Simulation", "Test Suite"],
)
st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Scope:** ADR-001 → ADR-004\n\n"
    "**Domain:** Autonomous drone fleets\n\n"
    "**Focus:** Fail-safe architecture, not flight physics"
)
st.sidebar.markdown(
    "[GitHub repo](https://github.com/joneslokouba-ui/ai-engineering-portfolio)"
)

# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------
if page == "Overview":
    st.title("Module 5: Sentinel Architecture")
    st.subheader("System Architecture for Safety-Critical Autonomous Drone AI")

    st.markdown(
        """
This module is not a flight simulator. It is an **architecture decision record (ADR) set**
plus a **discrete-event simulation** that proves the most important design decision in a
safety-critical AI system: the boundary between the AI stack and the flight-control loop
must never be crossed, even when the AI stack is wrong, slow, or under adversarial input.

Modules 1–4 demonstrated agent design, multi-agent orchestration, MLOps, and quantum ML.
This module demonstrates a different, senior-level skill: designing AI systems whose
mistakes have physical consequences — and proving, in code, that the safety boundary holds.
"""
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("ADRs Written", "4")
    col2.metric("Simulation Scenarios", "8")
    col3.metric("Scenarios Passing", "8 / 8")

    st.markdown("### What's actually proven here")
    st.markdown(
        """
- **ADR-001** — AI never has direct write access to flight control (whitelisted intent interface)
- **ADR-002** — Per-layer latency budgets with fail-fast behavior, not silent lateness
- **ADR-003** — A fixed four-state degradation ladder (NOMINAL → DEGRADED → LOST → FAIL_SAFE)
- **ADR-004** — Compound simultaneous failures escalate to FAIL_SAFE, closing a gap found during
  validation of ADR-003

Use the sidebar to explore the architecture diagrams, read the ADRs in full, run the
simulation interactively, or re-run the full 8-scenario test suite.
"""
    )

# ---------------------------------------------------------------------------
# System Architecture
# ---------------------------------------------------------------------------
elif page == "System Architecture":
    st.title("System Architecture")

    st.markdown("#### Layer diagram")
    st.caption(
        "The narrow arrow from Decision → Control is the single most important design "
        "decision in this system (ADR-001)."
    )
    mermaid(
        """
flowchart TB
    subgraph Onboard["Onboard Drone (Edge Compute)"]
        P[Perception Layer<br/>sensor fusion, edge inference]
        D[Decision Layer<br/>path planning, obstacle avoidance]
        C[Control Layer<br/>flight controller, hard real-time]
    end
    subgraph Ground["Ground Station"]
        G[Fleet/Ground Layer<br/>dashboard, logging, OTA updates]
    end
    Comm[Communication Layer<br/>telemetry link]
    P -->|"perception output (bounded, validated)"| D
    D -->|"control intent (bounded interface only)"| C
    C -->|actuator commands| Motors[Motors / Actuators]
    D <-.->|telemetry, link loss possible| Comm
    Comm <-.-> G
    style C fill:#c62828,color:#fff
    style D fill:#f9a825,color:#000
    style P fill:#0288d1,color:#fff
    style Comm fill:#757575,color:#fff
    style G fill:#2e7d32,color:#fff
""",
        height=440,
    )

    st.markdown("#### Failure scenario: sensor dropout → safe landing")
    mermaid(
        """
sequenceDiagram
    participant Sensor as Camera/LIDAR
    participant Perception as Perception Layer
    participant Decision as Decision Layer
    participant Control as Control Layer

    Sensor->>Perception: frame stream
    Note over Perception: frame timeout (>50ms)
    Perception->>Decision: STALE flag
    Decision->>Decision: confidence check fails
    Decision->>Control: DEGRADE_MODE: loiter
    Note over Control: only whitelisted intents accepted
    Control->>Control: execute pre-verified loiter
    Decision->>Decision: retry perception (bounded)
    alt sensor recovers
        Decision->>Control: RESUME_MODE
    else does not recover
        Decision->>Control: RETURN_TO_HOME
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
        choice = st.selectbox("Select an ADR", labels, index=min(1, len(labels) - 1))
        selected_path = ADR_DIR / f"{choice}.md"
        st.markdown(selected_path.read_text(encoding="utf-8"))

# ---------------------------------------------------------------------------
# Live Simulation
# ---------------------------------------------------------------------------
elif page == "Live Simulation":
    st.title("Live Simulation")
    st.caption(
        "Drive the Perception and Decision layers yourself and watch the Control layer "
        "enforce the fail-safe boundary in real time."
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### Perception layer input")
        latency = st.slider("Perception latency (ms)", 0, 150, 30, help="Budget is 50ms (ADR-002)")
        confidence = st.slider("Perception confidence", 0.0, 1.0, 0.9, 0.05)
    with col2:
        st.markdown("##### Comms input")
        comms_choice = st.selectbox(
            "Comms state", [s.name for s in DegradationState], index=0
        )
        comms_state = DegradationState[comms_choice]

    st.markdown("##### Adversarial intent injection (tests ADR-001)")
    inject = st.checkbox("Inject a malformed / out-of-envelope intent from the Decision layer")
    forced_intent = None
    if inject:
        c1, c2, c3 = st.columns(3)
        with c1:
            kind_raw = st.text_input("Intent kind (try garbage, e.g. FULL_THROTTLE_DIVE)", "FULL_THROTTLE_DIVE")
        with c2:
            velocity = st.number_input("Velocity (m/s)", value=999.0)
        with c3:
            tilt = st.number_input("Tilt (deg)", value=89.0)
        # Try to resolve to a real IntentType if the user typed a valid one;
        # otherwise keep it as a raw string, exactly like the sim's garbage-intent test.
        try:
            kind_val = IntentType(kind_raw)
        except ValueError:
            kind_val = kind_raw
        forced_intent = Intent(kind=kind_val, velocity_mps=velocity, tilt_deg=tilt)

    if st.button("Run through the pipeline", type="primary"):
        perception = PerceptionLayer().process(latency_ms=latency, confidence=confidence)
        state, intent = DecisionLayer().decide(
            perception, comms_state, latency_ms=20, forced_intent=forced_intent
        )
        control = ControlLayer()
        executed = control.execute(intent)

        st.markdown("---")
        r1, r2, r3 = st.columns(3)
        with r1:
            st.markdown("**Perception state**")
            st.markdown(state_badge(perception.state), unsafe_allow_html=True)
        with r2:
            st.markdown("**Aggregated decision state**")
            st.markdown(state_badge(state), unsafe_allow_html=True)
        with r3:
            st.markdown("**Executed intent**")
            kind_display = executed.kind.value if isinstance(executed.kind, IntentType) else executed.kind
            st.markdown(f"**{kind_display}**  \n{executed.velocity_mps} m/s, {executed.tilt_deg}°")

        if control.rejected_log:
            rejected = control.rejected_log[0]
            rejected_kind = rejected.kind.value if isinstance(rejected.kind, IntentType) else rejected.kind
            st.warning(
                f"⚠️ Control layer REJECTED the requested intent: **{rejected_kind}** "
                f"({rejected.velocity_mps} m/s, {rejected.tilt_deg}°) — fell back to the "
                f"pre-verified safe maneuver above. This is ADR-001 in action: the Decision "
                f"layer is never trusted, only checked."
            )
        else:
            st.success("✅ Requested intent passed Control layer validation and was executed as-is.")

# ---------------------------------------------------------------------------
# Test Suite
# ---------------------------------------------------------------------------
elif page == "Test Suite":
    st.title("Test Suite")
    st.caption(
        "Runs the same 8 scenarios from sim/failsafe_sim.py that validate ADR-001 through "
        "ADR-004. This is the exact proof, not a reimplementation."
    )

    if st.button("Run all 8 scenarios", type="primary"):
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