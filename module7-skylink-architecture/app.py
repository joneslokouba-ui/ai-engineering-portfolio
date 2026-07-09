"""
app.py — Module 7: Skylink Architecture Dashboard

Scope note: this dashboard visualizes exactly what has been built and proven —
ADR-001 through ADR-004 and the 13 validated simulation scenarios in
sim/skylink_sim.py. Same discipline as Modules 5 and 6: nothing here claims
more than what's actually backed by an ADR and a passing scenario.

Run locally:
    streamlit run app.py
"""

import io
import contextlib
from pathlib import Path

import streamlit as st

from sim.skylink_sim import (
    DegradationState,
    free_space_path_loss_db,
    doppler_shift_hz,
    slice_latency_ms,
    deployment_model_at,
    zone_transition_result,
    simulate_handovers,
    evaluate_handover_burden,
    isac_resource_allocation,
    isac_detection_effect,
    CARRIER_FREQ_HZ,
    LATENCY_BUDGET_MS,
    HANDOVER_SUBBUDGET_MS,
    GROUND_DEFAULT_HYSTERESIS_DB,
    AERIAL_OPTIMIZED_HYSTERESIS_DB,
    CELL_SPACING_M,
    ISAC_MULTISTATIC_MIN_NODES,
    run_all,
)

BASE_DIR = Path(__file__).parent
ADR_DIR = BASE_DIR / "adr"

st.set_page_config(
    page_title="Module 7: Skylink Architecture",
    page_icon="📡",
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
st.sidebar.title("📡 Skylink Architecture")
st.sidebar.caption("Module 7 — AI Engineering Portfolio")
page = st.sidebar.radio(
    "Navigate",
    ["Overview", "System Architecture", "ADR Browser", "Live Simulation", "Test Suite"],
)
st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Scope:** ADR-001 → ADR-004\n\n"
    "**Domain:** 5G Standalone connectivity for UAV/AAM operations\n\n"
    "**Focus:** Network architecture, not a production RF simulator\n\n"
    "**Built in:** Python — see Overview for why not C++"
)
st.sidebar.markdown(
    "[GitHub repo](https://github.com/joneslokouba-ui/ai-engineering-portfolio)"
)

# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------
if page == "Overview":
    st.title("Module 7: Skylink Architecture")
    st.subheader("Digital Airspace Connectivity — the Communication Layer Module 5 Left Abstract")

    st.markdown(
        """
Module 5 (Sentinel Architecture) drew a system diagram with a **Communication Layer** box —
"drone-to-ground telemetry, link loss possible" — and deliberately left it abstract. This module
builds out exactly that box: how a UAV's Command & Control (C2) link, payload telemetry, and UTM
connectivity are actually carried over a real 5G Standalone network, grounded in Ericsson's public
"5G — A key enabler for Air Traffic Control" paper (2025).

**Why Python, not C++:** the physics here — free-space path loss, Doppler shift, antenna gain
patterns, handover-latency modeling — is pure math. C++ earns its place when the claim is about a
real-time embedded control loop on constrained hardware (as in Module 5's flight controller).
Modeling RF propagation and network architecture doesn't need that.
"""
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("ADRs Written", "4")
    col2.metric("Simulation Scenarios", "13")
    col3.metric("Scenarios Passing", "13 / 13")

    st.markdown("### What's actually proven here")
    st.markdown(
        """
- **ADR-001** — mission-critical C2/UTM traffic rides a dedicated, SLA-guaranteed network slice,
  isolated from general public traffic — never a silent fallback to best-effort capacity
- **ADR-002** — deployment model (FAA Private / MNO Slice / Hybrid) is selected by zone
  classification, not applied uniformly nationwide
- **ADR-003** — aerial UEs use a dedicated cell layer with bounded handover latency; a real
  antenna sidelobe-ripple model shows default ground-optimized mobility "ping-ponging" between
  cells, while an aerial-optimized policy stays within budget
- **ADR-004** — ISAC drone detection (radar-like sensing for unconnected UAVs) is
  resource-subordinate to the C2/UTM slice, and a single detection alone can never affect a
  connected UAV's state — only multi-static corroboration can, and even then only to an advisory
  level, never an autonomous high-consequence action

This is the **third module in a row** where a probabilistic or automated signal is architected to
*propose, never command* — after Module 5's AI/flight-control boundary and Module 6's
fraud-model/Tier-2 boundary. Same pattern, third domain.

Use the sidebar to explore the architecture diagrams, read the ADRs in full, run the physics and
decision models interactively, or re-run the full 13-scenario test suite.
"""
    )

# ---------------------------------------------------------------------------
# System Architecture
# ---------------------------------------------------------------------------
elif page == "System Architecture":
    st.title("System Architecture")

    st.markdown("#### Connectivity layer diagram")
    st.caption(
        "The separation between the dedicated C2/UTM slice and the general public slice is this "
        "module's flagship decision (ADR-001) — feeding directly into Module 5's Communication Layer."
    )
    mermaid(
        """
flowchart TB
    subgraph Altitudes["Altitude-dependent connectivity needs"]
        Low["Low altitude <1,000 ft"]
        Med["Medium altitude 1,000-10,000 ft"]
        High["High altitude 10,000-40,000 ft"]
    end
    subgraph UAV["UAV / AAM Platform"]
        C2[C2 Link<br/>VLOS / BVLOS control]
        Payload[Payload Comms]
        UTMLink[UTM Connectivity]
    end
    subgraph Network["5G Standalone Network"]
        Slice1["Dedicated C2/UTM Slice<br/>guaranteed QoS, isolated"]
        Slice2["General Public Slice<br/>best-effort"]
        Ground["Ground Infrastructure<br/>430,000+ US cellular sites"]
    end
    subgraph Consumers["Consumes this layer"]
        M5["Module 5: Sentinel Architecture<br/>Communication Layer"]
    end
    C2 -->|mission-critical| Slice1
    UTMLink -->|mission-critical| Slice1
    Payload -.->|best-effort| Slice2
    Slice1 --> Ground
    Slice2 --> Ground
    Slice1 -->|telemetry, link-loss signal| M5
    style Slice1 fill:#2e7d32,color:#fff
    style Slice2 fill:#757575,color:#fff
    style C2 fill:#0288d1,color:#fff
    style M5 fill:#f9a825,color:#000
""",
        height=440,
    )

    st.markdown("#### Aerial handover: ping-pong vs. aerial-optimized mobility")
    st.caption(
        "Ground-optimized antennas serve aerial UEs via sidelobes, causing elevated interference "
        "and frequent handovers at medium altitude (ADR-003)."
    )
    mermaid(
        """
sequenceDiagram
    participant UAV
    participant CellA as Ground Cell A
    participant CellB as Ground Cell B
    participant Ladder as Module 5 Degradation Ladder

    UAV->>CellA: served (sidelobe gain)
    Note over UAV: crosses overlap region<br/>sidelobe ripple causes signal to oscillate
    UAV->>CellB: handover (default 2dB hysteresis)
    UAV->>CellA: handover back (ping-pong)
    UAV->>CellB: handover again
    Note over UAV,Ladder: stacked handovers breach 5ms sub-budget
    UAV->>Ladder: report DEGRADED

    Note over UAV: with aerial-cell config (6dB hysteresis)
    UAV->>CellB: single clean handover, within budget
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
    st.caption("Four sub-models, one per ADR. Pick a section below.")

    section = st.radio(
        "Model",
        ["Network Slice Load (ADR-001)", "Zone Deployment (ADR-002)",
         "Aerial Handover (ADR-003)", "ISAC Detection (ADR-004)"],
        horizontal=True,
    )

    if section == "Network Slice Load (ADR-001)":
        st.markdown("##### Drive background network load and compare isolated vs. shared latency")
        background_load = st.slider("Background (public traffic) load", 0.0, 0.98, 0.60, 0.01)

        if st.button("Run slice comparison", type="primary"):
            iso_latency, iso_state = slice_latency_ms(background_load, isolated=True)
            shared_latency, shared_state = slice_latency_ms(background_load, isolated=False)

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Isolated C2/UTM slice (ADR-001)**")
                st.markdown(state_badge(iso_state), unsafe_allow_html=True)
                st.metric("Latency", f"{iso_latency:.1f} ms" if iso_latency != float("inf") else "slice saturated")
            with c2:
                st.markdown("**Shared / non-isolated network**")
                st.markdown(state_badge(shared_state), unsafe_allow_html=True)
                st.metric("Latency", f"{shared_latency:.1f} ms")

            if shared_latency > LATENCY_BUDGET_MS >= iso_latency:
                st.success(
                    f"At {background_load:.0%} background load, the isolated slice stays within "
                    f"the {LATENCY_BUDGET_MS:.0f}ms SLA while the shared network breaches it — "
                    f"exactly the case ADR-001 exists to prevent."
                )

    elif section == "Zone Deployment (ADR-002)":
        st.markdown("##### Query the deployment model at any point along a flight path")
        position_km = st.slider("Flight path position (km)", 0.0, 15.0, 5.0, 0.1)
        model = deployment_model_at(position_km)
        st.markdown(f"**Deployment model at {position_km:.1f} km:** {model}")

        st.markdown("##### Simulate a zone-boundary handover")
        gap = st.checkbox("Simulate a handover gap at the boundary")
        state = zone_transition_result(position_km, handover_gap_detected=gap)
        st.markdown(state_badge(state), unsafe_allow_html=True)

    elif section == "Aerial Handover (ADR-003)":
        st.markdown("##### Compare ground-optimized vs. aerial-optimized mobility hysteresis")
        custom_hysteresis = st.slider("Hysteresis margin (dB)", 1.0, 10.0, GROUND_DEFAULT_HYSTERESIS_DB, 0.5)

        if st.button("Run handover simulation", type="primary"):
            midpoint = CELL_SPACING_M / 2
            handovers = simulate_handovers(custom_hysteresis, midpoint - 300, midpoint + 300, step_m=5.0)
            worst_cluster_ms, state = evaluate_handover_burden(handovers)

            c1, c2, c3 = st.columns(3)
            c1.metric("Handover count", len(handovers))
            c2.metric("Worst stacked cluster", f"{worst_cluster_ms:.1f} ms")
            with c3:
                st.markdown("**State**")
                st.markdown(state_badge(state), unsafe_allow_html=True)

            st.caption(
                f"Sub-budget: {HANDOVER_SUBBUDGET_MS:.0f}ms. Default ground hysteresis is "
                f"{GROUND_DEFAULT_HYSTERESIS_DB:.0f}dB (ping-pong); aerial-optimized is "
                f"{AERIAL_OPTIMIZED_HYSTERESIS_DB:.0f}dB (clean handover)."
            )

    elif section == "ISAC Detection (ADR-004)":
        st.markdown("##### Resource contention: C2 slice vs. ISAC sensing demand")
        c1, c2 = st.columns(2)
        with c1:
            background_load = st.slider("Background load", 0.0, 0.9, 0.65, 0.05, key="isac_bg")
        with c2:
            isac_requested = st.slider("ISAC requested capacity fraction", 0.0, 1.0, 0.90, 0.05)

        if st.button("Run resource allocation", type="primary"):
            c2_latency, isac_allocated, c2_state = isac_resource_allocation(background_load, isac_requested)
            r1, r2 = st.columns(2)
            with r1:
                st.markdown("**C2/UTM slice**")
                st.markdown(state_badge(c2_state), unsafe_allow_html=True)
                st.metric("Latency", f"{c2_latency:.1f} ms")
            with r2:
                st.markdown("**ISAC allocation**")
                st.metric("Allocated (of requested)", f"{isac_allocated:.2f} / {isac_requested:.2f}")
            if isac_allocated < isac_requested:
                st.info("ISAC was throttled to protect the C2/UTM slice's guarantee — never the reverse.")

        st.markdown("---")
        st.markdown("##### Detection corroboration")
        nodes = st.slider("Corroborating sensing nodes", 0, 10, 1)
        state = isac_detection_effect(nodes)
        st.markdown(state_badge(state), unsafe_allow_html=True)
        if nodes < ISAC_MULTISTATIC_MIN_NODES:
            st.caption(f"Below the {ISAC_MULTISTATIC_MIN_NODES}-node corroboration threshold — zero effect on connected-UAV state.")
        else:
            st.caption("Corroboration threshold met — advisory DEGRADED state only, never an autonomous action, no matter how many nodes agree.")

# ---------------------------------------------------------------------------
# Test Suite
# ---------------------------------------------------------------------------
elif page == "Test Suite":
    st.title("Test Suite")
    st.caption(
        "Runs the same 13 scenarios from sim/skylink_sim.py that validate ADR-001 through "
        "ADR-004. This is the exact proof, not a reimplementation."
    )

    if st.button("Run all 13 scenarios", type="primary"):
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