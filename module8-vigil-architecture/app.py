"""
app.py — Module 8: Vigil Architecture Dashboard

Scope note: this dashboard visualizes exactly what has been built and proven —
ADR-001 through ADR-004 and the 11 validated simulation scenarios in
sim/vigil_sim.py. This is NOT a diagnostic tool and produces no real medical
output — every "condition" name in the interactive demo is a placeholder
string used to prove the architecture, not a real clinical suggestion.

Run locally:
    streamlit run app.py
"""

import io
import contextlib
from pathlib import Path

import streamlit as st

from sim.vigil_sim import (
    DataProvenance,
    ConfidenceBand,
    DiagnosticContextLayer,
    get_regional_data,
    get_regional_data_with_fallback,
    SEVERITY_WATCHLIST,
    MOCK_DATA_STORE,
    run_all,
)

BASE_DIR = Path(__file__).parent
ADR_DIR = BASE_DIR / "adr"

st.set_page_config(
    page_title="Module 8: Vigil Architecture",
    page_icon="🩺",
    layout="wide",
)

PROVENANCE_COLORS = {
    DataProvenance.DIRECT: "#2e7d32",
    DataProvenance.REGIONAL_FALLBACK: "#f9a825",
    DataProvenance.GLOBAL_FALLBACK: "#ef6c00",
    DataProvenance.UNKNOWN: "#c62828",
}

BAND_COLORS = {
    ConfidenceBand.STRONG: "#2e7d32",
    ConfidenceBand.MODERATE: "#0288d1",
    ConfidenceBand.WEAK: "#f9a825",
    ConfidenceBand.UNKNOWN: "#757575",
}


def badge(text: str, color: str) -> str:
    return (
        f"<span style='background-color:{color};color:white;padding:4px 12px;"
        f"border-radius:12px;font-weight:600;font-size:0.85rem'>{text}</span>"
    )


def mermaid(code: str, height: int = 440) -> None:
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
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.title("🩺 Vigil Architecture")
st.sidebar.caption("Module 8 — AI Engineering Portfolio")
page = st.sidebar.radio(
    "Navigate",
    ["Overview", "System Architecture", "ADR Browser", "Live Simulation", "Test Suite"],
)
st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Scope:** ADR-001 → ADR-004\n\n"
    "**Domain:** AMR surveillance + diagnostic context\n\n"
    "**Focus:** Zero autonomous tier — a decision-support architecture, not a diagnostic tool\n\n"
    "**Grounded in:** WHO GLASS 2025 report"
)
st.sidebar.warning("This is a portfolio architecture demo. It produces no real medical output.")
st.sidebar.markdown(
    "[GitHub repo](https://github.com/joneslokouba-ui/ai-engineering-portfolio)"
)

# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------
if page == "Overview":
    st.title("Module 8: Vigil Architecture")
    st.subheader("AMR Surveillance & Diagnostic Context — the Strictest Authority Boundary Yet")

    st.markdown(
        """
Modules 5, 6, and 7 each bounded an automated tier. This module has **no autonomous tier at all**
— every output is a ranked set of possibilities with explicit uncertainty, for a clinician to
weigh. Grounded in WHO's real 2025 GLASS report (23M+ confirmed infections, 104 reporting
countries, ~1-in-6 infections resistant globally).
"""
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("ADRs Written", "4")
    col2.metric("Simulation Scenarios", "11")
    col3.metric("Scenarios Passing", "11 / 11")

    st.markdown("### What's actually proven here")
    st.markdown(
        """
- **ADR-001** — the system never outputs a diagnosis or treatment — only ranked possibilities
  with uncertainty. An adversarial "force a single answer" input has no code path to succeed.
- **ADR-002** — missing regional data is an explicit `UNKNOWN` state, never a numeric default;
  stale data is flagged; fallback estimates are tagged and confidence-penalized, never shown as
  equivalent to direct measurement.
- **ADR-003** — confidence is shown as qualitative bands with inline evidence and a persistent
  "not a diagnosis" header — never a bare list or a false-precision percentage.
- **ADR-004** — severity-flagged and WHO-reportable conditions can never be silently dropped by
  ranking alone, even when they rank low on likelihood.

This is the **fourth module in a row** using the "propose, never command" pattern — here taken to
its logical limit: zero autonomy, not just bounded autonomy.
"""
    )

# ---------------------------------------------------------------------------
# System Architecture
# ---------------------------------------------------------------------------
elif page == "System Architecture":
    st.title("System Architecture")
    st.caption("Notice: no arrow in this diagram points to an autonomous action.")
    mermaid(
        """
flowchart TB
    subgraph Surveillance["Population-Level (WHO GLASS-style aggregate data)"]
        Ingest["Surveillance Ingestion Layer"]
        Trend["Trend/Anomaly Detection Layer"]
    end
    subgraph Diagnostic["Patient-Level (clinician-entered, no PHI stored)"]
        Context["Diagnostic Context Layer<br/>ranks possibilities + confidence bands"]
    end
    subgraph Human["Human Authority — No Autonomous Tier"]
        Clinician["Clinician Decision Layer<br/>the ONLY layer that acts"]
    end
    Audit["Audit/Provenance Layer"]
    Ingest --> Trend --> Context
    Context -->|"ranked possibilities + uncertainty<br/>never a diagnosis"| Clinician
    Ingest -.->|logged| Audit
    Context -.->|logged| Audit
    Clinician -.->|decision + rationale logged| Audit
    style Clinician fill:#c62828,color:#fff
    style Context fill:#f9a825,color:#000
    style Trend fill:#0288d1,color:#fff
    style Ingest fill:#5bc0de,color:#000
    style Audit fill:#2e7d32,color:#fff
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
        st.error("No ADR files found.")
    else:
        labels = [f.stem for f in adr_files]
        choice = st.selectbox("Select an ADR", labels, index=0)
        st.markdown((ADR_DIR / f"{choice}.md").read_text(encoding="utf-8"))

# ---------------------------------------------------------------------------
# Live Simulation
# ---------------------------------------------------------------------------
elif page == "Live Simulation":
    st.title("Live Simulation")
    st.caption("Placeholder condition names only — this proves the architecture, not real diagnostics.")

    st.markdown("##### Regional surveillance data (ADR-002)")
    region = st.selectbox("Region", ["region_a (fresh, direct)", "region_b (stale)", "region_z (unknown)"])
    region_key = region.split(" ")[0]
    use_fallback = st.checkbox("Use fallback estimate if region is UNKNOWN")

    if use_fallback:
        regional = get_regional_data_with_fallback(region_key, "E.coli", "ciprofloxacin")
    else:
        regional = get_regional_data(region_key, "E.coli", "ciprofloxacin")

    c1, c2, c3 = st.columns(3)
    c1.markdown("**Provenance**")
    c1.markdown(badge(regional.provenance.value, PROVENANCE_COLORS[regional.provenance]), unsafe_allow_html=True)
    c2.metric("Report year", regional.report_year if regional.report_year else "—")
    c3.metric("Stale?", "Yes" if regional.is_stale else "No")

    st.markdown("---")
    st.markdown("##### Diagnostic context generation (ADR-001, ADR-003, ADR-004)")
    include_severity = st.checkbox("Include a severity-flagged (watch-list) condition, ranked last", value=True)
    force_single = st.checkbox("Try to force a single-answer output (adversarial test of ADR-001)")

    candidates = ["common_cold", "seasonal_flu", "viral_pharyngitis"]
    if include_severity:
        candidates.append(next(iter(SEVERITY_WATCHLIST)))

    if st.button("Generate differential context", type="primary"):
        layer = DiagnosticContextLayer()
        output = layer.generate(candidates, regional, force_single_answer=force_single)

        st.info(f"**{output.framing_header}**")

        st.markdown("**Ranked list (ADR-003)**")
        for item in output.items:
            st.markdown(
                f"- **{item.condition}** — "
                f"{badge(item.confidence_band.value, BAND_COLORS[item.confidence_band])}",
                unsafe_allow_html=True,
            )
            if item.data_flags:
                st.caption(" · ".join(item.data_flags))

        if output.severity_section:
            st.markdown("**⚠️ Severity/reportability floor (ADR-004) — never suppressed by ranking**")
            for item in output.severity_section:
                st.markdown(f"- **{item.condition}** — {item.evidence[0]}")
        else:
            st.caption("No watch-list conditions excluded from the ranked list this run.")

        st.success(f"Output item count: {len(output.items)} (never fewer than 2, even with force_single_answer requested).")

# ---------------------------------------------------------------------------
# Test Suite
# ---------------------------------------------------------------------------
elif page == "Test Suite":
    st.title("Test Suite")
    st.caption(
        "Runs the same 11 scenarios from sim/vigil_sim.py that validate ADR-001 through "
        "ADR-004. This is the exact proof, not a reimplementation."
    )

    if st.button("Run all 11 scenarios", type="primary"):
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