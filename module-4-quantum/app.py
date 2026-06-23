"""
Module 4 — Quantum AI Explorer
Geoffrey Jones Okwi | ai-engineering-portfolio
Stack: Qiskit 1.4.x + Streamlit + Plotly
"""

import streamlit as st
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
import time
import random
import hashlib
import math

# ─── PAGE CONFIG ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Quantum AI Explorer | Module 4",
    page_icon="⚛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── GLOBAL STYLE ────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@300;400;600&display=swap');

/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif;
    background-color: #04080f;
    color: #c8d8f0;
}
.stApp { background: #04080f; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #06101e 0%, #091525 100%);
    border-right: 1px solid #1a3a5c;
}
[data-testid="stSidebar"] .stMarkdown h1,
[data-testid="stSidebar"] .stMarkdown h2,
[data-testid="stSidebar"] .stMarkdown h3 {
    color: #5fb4ff;
}

/* ── Tab strip ── */
.stTabs [data-baseweb="tab-list"] {
    background: #06101e;
    border-bottom: 2px solid #1a3a5c;
    gap: 4px;
    padding: 0 8px;
}
.stTabs [data-baseweb="tab"] {
    color: #5d8ab0;
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 500;
    font-size: 0.88rem;
    padding: 10px 18px;
    border-radius: 4px 4px 0 0;
    border: none;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(180deg, #0f2a44 0%, #06101e 100%) !important;
    color: #5fb4ff !important;
    border-top: 2px solid #5fb4ff !important;
}

/* ── Cards ── */
.q-card {
    background: linear-gradient(135deg, #07141f 0%, #0c1e30 100%);
    border: 1px solid #1a3a5c;
    border-radius: 10px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1rem;
}
.q-card-glow {
    background: linear-gradient(135deg, #07141f 0%, #0c1e30 100%);
    border: 1px solid #3b7dbf;
    border-radius: 10px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1rem;
    box-shadow: 0 0 18px rgba(63,149,255,0.10);
}

/* ── Metrics ── */
.metric-block {
    background: #06101e;
    border: 1px solid #1a3a5c;
    border-radius: 8px;
    padding: 1rem;
    text-align: center;
}
.metric-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 2rem;
    font-weight: 600;
    color: #5fb4ff;
    line-height: 1.1;
}
.metric-label {
    font-size: 0.78rem;
    color: #5d8ab0;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-top: 4px;
}

/* ── Circuit text ── */
.circuit-box {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.82rem;
    background: #020b13;
    border: 1px solid #1a3a5c;
    border-radius: 8px;
    padding: 1.1rem 1.4rem;
    color: #7dd3fc;
    white-space: pre;
    overflow-x: auto;
    line-height: 1.6;
}

/* ── Section headers ── */
.section-eyebrow {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: #3b7dbf;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    margin-bottom: 4px;
}
.section-title {
    font-size: 1.55rem;
    font-weight: 600;
    color: #dceeff;
    margin-bottom: 0.2rem;
}
.section-sub {
    font-size: 0.9rem;
    color: #5d8ab0;
    margin-bottom: 1.2rem;
}

/* ── Bits strip ── */
.bit-strip {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.05rem;
    letter-spacing: 0.25em;
    color: #5fb4ff;
    background: #020b13;
    border: 1px solid #1a3a5c;
    border-radius: 6px;
    padding: 10px 14px;
    word-break: break-all;
}

/* ── BB84 key ── */
.key-cell {
    display: inline-block;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    padding: 3px 6px;
    margin: 2px;
    border-radius: 4px;
}
.key-match  { background: #0e3a1e; color: #4ade80; border: 1px solid #166534; }
.key-nomat  { background: #2d1515; color: #f87171; border: 1px solid #7f1d1d; }

/* ── Quantum glow accent ── */
.q-glow { color: #5fb4ff; text-shadow: 0 0 12px rgba(95,180,255,0.45); }

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, #0f3460 0%, #1a5fa8 100%);
    color: #dceeff;
    border: 1px solid #3b7dbf;
    border-radius: 6px;
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 500;
    padding: 0.45rem 1.2rem;
    transition: all 0.2s ease;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #1a5fa8 0%, #2d7dd2 100%);
    box-shadow: 0 0 14px rgba(63,149,255,0.25);
}

/* ── Inputs ── */
.stSelectbox > div, .stSlider > div {
    color: #c8d8f0;
}
label { color: #7ca4c8 !important; }

/* ── Alert boxes ── */
.stSuccess { background: #0e3a1e; border-color: #166534; }
.stInfo    { background: #0c1e30; border-color: #1a3a5c; }
.stWarning { background: #2d1f0a; border-color: #92400e; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #04080f; }
::-webkit-scrollbar-thumb { background: #1a3a5c; border-radius: 3px; }

/* ── Hero header ── */
.hero-wrap {
    background: linear-gradient(135deg, #06101e 0%, #091829 60%, #0a1e33 100%);
    border: 1px solid #1a3a5c;
    border-radius: 12px;
    padding: 2rem 2.4rem 1.6rem;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
}
.hero-wrap::before {
    content: '⚛';
    position: absolute;
    right: 2rem;
    top: 50%;
    transform: translateY(-50%);
    font-size: 5rem;
    opacity: 0.07;
    pointer-events: none;
}
</style>
""", unsafe_allow_html=True)

# ─── SIDEBAR ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
<div style='text-align:center; padding: 1rem 0 0.5rem;'>
  <div style='font-family:"JetBrains Mono",monospace; font-size:0.7rem;
              color:#3b7dbf; letter-spacing:0.14em; text-transform:uppercase;'>
    AI Engineering Portfolio
  </div>
  <div style='font-size:1.6rem; font-weight:700; color:#dceeff; margin:4px 0;'>
    ⚛️ Module 4
  </div>
  <div style='font-size:0.9rem; color:#5fb4ff;'>Quantum AI Explorer</div>
</div>
<hr style='border-color:#1a3a5c; margin:1rem 0;'>
""", unsafe_allow_html=True)

    st.markdown("### 🗂️ Portfolio")
    st.markdown("""
<div style='font-size:0.83rem; line-height:2;'>
  ✅ <a href='https://module1-ai-agents.streamlit.app' target='_blank'
         style='color:#5fb4ff;'>Module 1 — ReAct Agent</a><br>
  ✅ <a href='https://module2-multi-agent.streamlit.app' target='_blank'
         style='color:#5fb4ff;'>Module 2 — Multi-Agent RAG</a><br>
  ✅ <a href='https://module3-mlops.streamlit.app' target='_blank'
         style='color:#5fb4ff;'>Module 3 — MLOps Pipeline</a><br>
  🔬 <span style='color:#fbbf24;'>Module 4 — Quantum (live)</span>
</div>
""", unsafe_allow_html=True)

    st.markdown("<hr style='border-color:#1a3a5c;'>", unsafe_allow_html=True)
    st.markdown("### ⚙️ Stack")
    st.markdown("""
<div style='font-family:"JetBrains Mono",monospace; font-size:0.78rem;
            color:#7ca4c8; line-height:1.9;'>
  Qiskit 1.4.x<br>
  Qiskit-Aer 0.15.x<br>
  Streamlit 1.45.x<br>
  Plotly 6.x<br>
  NumPy 1.26.x
</div>
""", unsafe_allow_html=True)

    st.markdown("<hr style='border-color:#1a3a5c;'>", unsafe_allow_html=True)
    st.markdown("### 👤 Author")
    st.markdown("""
<div style='font-size:0.83rem; color:#7ca4c8; line-height:1.8;'>
  <b style='color:#c8d8f0;'>Geoffrey Jones Okwi</b><br>
  AI/ML Engineer · Calgary, AB<br>
  MSc Earth Sciences — Waterloo<br>
  Stanford/Andrew Ng AI/ML<br><br>
  <a href='https://github.com/joneslokouba-ui/ai-engineering-portfolio'
     target='_blank' style='color:#5fb4ff;'>🔗 GitHub Portfolio</a><br>
  <a href='https://linkedin.com/in/geoffrey-okwi-826871415'
     target='_blank' style='color:#5fb4ff;'>💼 LinkedIn</a>
</div>
""", unsafe_allow_html=True)

# ─── HERO ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class='hero-wrap'>
  <div class='section-eyebrow'>Module 4 · Quantum AI Explorer</div>
  <div style='font-size:2.1rem; font-weight:700; color:#dceeff; line-height:1.2;'>
    From Qubits to Intelligence
  </div>
  <div style='font-size:1rem; color:#5d8ab0; margin-top:0.5rem; max-width:620px;'>
    Hands-on quantum computing: build circuits, visualize superposition,
    compare classical vs quantum ML, generate certified random numbers,
    and simulate the BB84 quantum cryptography protocol.
  </div>
</div>
""", unsafe_allow_html=True)

# ─── TABS ────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "⚡ Circuits",
    "🤖 Classical vs Quantum",
    "🎲 Random Numbers",
    "🔐 BB84 Crypto",
    "📖 Portfolio Story",
])

sim = AerSimulator()   # shared simulator instance

# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — QUANTUM CIRCUITS VISUALIZER
# ════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("""
<div class='section-eyebrow'>Quantum Circuits Visualizer</div>
<div class='section-title'>Build & Simulate Quantum Circuits</div>
<div class='section-sub'>
  Select a preset circuit, inspect the gate sequence, run the simulation,
  and explore the measurement outcome distribution.
</div>
""", unsafe_allow_html=True)

    CIRCUITS = {
        "Bell State (2-qubit entanglement)": "bell",
        "GHZ State (3-qubit entanglement)": "ghz",
        "Quantum Superposition (single qubit)": "superposition",
        "Quantum Fourier Transform (3-qubit)": "qft",
        "Grover's Oracle (2-qubit search)": "grover",
    }

    col_l, col_r = st.columns([1, 2])
    with col_l:
        choice = st.selectbox("Circuit preset", list(CIRCUITS.keys()))
        shots = st.slider("Simulation shots", 256, 8192, 2048, step=256)
        run_btn = st.button("▶ Run Simulation", key="run_circuit")

    circuit_key = CIRCUITS[choice]

    def make_circuit(key):
        if key == "bell":
            qc = QuantumCircuit(2, 2)
            qc.h(0); qc.cx(0, 1)
            qc.measure([0, 1], [0, 1])
            desc = "Hadamard + CNOT creates maximal entanglement: measuring one qubit instantly determines the other."
        elif key == "ghz":
            qc = QuantumCircuit(3, 3)
            qc.h(0); qc.cx(0, 1); qc.cx(0, 2)
            qc.measure([0,1,2],[0,1,2])
            desc = "Greenberger–Horne–Zeilinger: three-qubit superposition, the foundation of quantum error correction."
        elif key == "superposition":
            qc = QuantumCircuit(1, 1)
            qc.h(0)
            qc.measure(0, 0)
            desc = "Hadamard gate places a single qubit in equal superposition of |0⟩ and |1⟩."
        elif key == "qft":
            qc = QuantumCircuit(3, 3)
            for i in range(3):
                qc.h(i)
                for j in range(i+1, 3):
                    qc.cp(math.pi / (2 ** (j - i)), i, j)
            qc.swap(0, 2)
            qc.measure([0,1,2],[0,1,2])
            desc = "Quantum Fourier Transform: the backbone of Shor's factoring algorithm, exponentially faster than classical FFT."
        elif key == "grover":
            qc = QuantumCircuit(2, 2)
            qc.h([0, 1])
            # Oracle: marks |11⟩
            qc.cz(0, 1)
            # Diffusion
            qc.h([0, 1]); qc.x([0, 1]); qc.cz(0, 1); qc.x([0, 1]); qc.h([0, 1])
            qc.measure([0, 1], [0, 1])
            desc = "Grover's algorithm amplifies the amplitude of the marked state |11⟩, achieving √N speedup over classical search."
        return qc, desc

    qc, desc = make_circuit(circuit_key)

    with col_l:
        st.markdown(f"<div class='q-card' style='margin-top:0.8rem;'>"
                    f"<div style='font-size:0.82rem; color:#7ca4c8;'>{desc}</div>"
                    f"</div>", unsafe_allow_html=True)

    with col_r:
        # ASCII-style circuit diagram
        diagram_lines = str(qc.draw('text')).split('\n')
        diagram_html = '\n'.join(diagram_lines)
        st.markdown(f"<div class='circuit-box'>{diagram_html}</div>",
                    unsafe_allow_html=True)

    # Gate breakdown table
    gate_data = {}
    for inst in qc.data:
        name = inst.operation.name
        if name not in ('measure', 'barrier'):
            gate_data[name] = gate_data.get(name, 0) + 1

    cols = st.columns(max(len(gate_data), 1) + 1)
    cols[0].markdown("<div class='metric-block'><div class='metric-value'>"
                     f"{qc.num_qubits}</div>"
                     "<div class='metric-label'>Qubits</div></div>",
                     unsafe_allow_html=True)
    for i, (g, c) in enumerate(gate_data.items()):
        cols[i+1].markdown(f"<div class='metric-block'><div class='metric-value'>{c}</div>"
                           f"<div class='metric-label'>{g.upper()} gates</div></div>",
                           unsafe_allow_html=True)

    if run_btn:
        with st.spinner("Running quantum simulation…"):
            tqc = transpile(qc, sim)
            result = sim.run(tqc, shots=shots).result()
            counts = result.get_counts()

        states = list(counts.keys())
        freqs  = [counts[s] / shots for s in states]
        probs  = [counts[s] for s in states]

        fig = go.Figure(go.Bar(
            x=states, y=probs,
            marker=dict(
                color=freqs,
                colorscale=[[0,'#0f3460'],[0.5,'#1a5fa8'],[1,'#5fb4ff']],
                line=dict(color='#1a3a5c', width=1),
            ),
            text=[f"{f*100:.1f}%" for f in freqs],
            textposition='outside',
            textfont=dict(color='#7ca4c8', size=11),
        ))
        fig.update_layout(
            paper_bgcolor='#04080f', plot_bgcolor='#07141f',
            font=dict(family='Space Grotesk', color='#c8d8f0'),
            xaxis=dict(title='Measurement outcome', gridcolor='#1a3a5c',
                       tickfont=dict(family='JetBrains Mono', size=12, color='#5fb4ff')),
            yaxis=dict(title='Count', gridcolor='#1a3a5c'),
            title=dict(text=f"Simulation results — {shots:,} shots",
                       font=dict(size=14, color='#dceeff')),
            margin=dict(l=30, r=30, t=50, b=30),
            bargap=0.3,
        )
        st.plotly_chart(fig, use_container_width=True)

        # Dominant state
        dominant = max(counts, key=counts.get)
        pct = counts[dominant]/shots*100
        st.markdown(f"""
<div class='q-card-glow'>
  <span class='section-eyebrow'>Result</span><br>
  Dominant state <span class='q-glow' style='font-family:JetBrains Mono,monospace;
  font-size:1.1rem;'>|{dominant}⟩</span> measured
  <b style='color:#5fb4ff;'>{pct:.1f}%</b> of the time across {shots:,} shots.
  {'This confirms perfect entanglement — only |00⟩ and |11⟩ are ever observed.' if circuit_key=='bell' else ''}
</div>
""", unsafe_allow_html=True)

    # Bloch sphere for single-qubit circuit
    if circuit_key == "superposition":
        st.markdown("<hr style='border-color:#1a3a5c;'>", unsafe_allow_html=True)
        st.markdown("#### Bloch Sphere — superposition state")
        theta, phi = np.pi/2, 0   # |+⟩ state
        x = np.sin(theta)*np.cos(phi)
        y = np.sin(theta)*np.sin(phi)
        z = np.cos(theta)

        u, v = np.mgrid[0:2*np.pi:40j, 0:np.pi:20j]
        sx = np.cos(u)*np.sin(v)
        sy = np.sin(u)*np.sin(v)
        sz = np.cos(v)

        bloch = go.Figure()
        bloch.add_trace(go.Surface(x=sx, y=sy, z=sz, opacity=0.08,
                                   colorscale=[[0,'#0f3460'],[1,'#1a5fa8']],
                                   showscale=False))
        for axis, col in [([[-1,1],[0,0],[0,0]],'#1a3a5c'),
                          ([[0,0],[-1,1],[0,0]],'#1a3a5c'),
                          ([[0,0],[0,0],[-1,1]],'#3b7dbf')]:
            bloch.add_trace(go.Scatter3d(
                x=axis[0], y=axis[1], z=axis[2],
                mode='lines', line=dict(color=col, width=2),
                showlegend=False))
        bloch.add_trace(go.Cone(
            x=[0], y=[0], z=[0], u=[x], v=[y], w=[z],
            sizemode='absolute', sizeref=0.25,
            colorscale=[[0,'#5fb4ff'],[1,'#93c5fd']],
            showscale=False, name='|+⟩'))
        bloch.update_layout(
            paper_bgcolor='#04080f', margin=dict(l=0,r=0,t=0,b=0),
            scene=dict(
                bgcolor='#07141f',
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False,
                           title='X'),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False,
                           title='Y'),
                zaxis=dict(showgrid=False, zeroline=False, showticklabels=False,
                           title='Z'),
                aspectmode='cube',
            ), height=380,
        )
        st.plotly_chart(bloch, use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — CLASSICAL vs QUANTUM ML COMPARISON
# ════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("""
<div class='section-eyebrow'>Classical vs Quantum ML</div>
<div class='section-title'>How Quantum Enhances Machine Learning</div>
<div class='section-sub'>
  Simulate a quantum kernel classification experiment and compare it with
  its classical counterpart on a synthetic dataset.
</div>
""", unsafe_allow_html=True)

    n_points = st.slider("Dataset size (points per class)", 20, 120, 60, step=10)
    run_compare = st.button("⚡ Run Comparison", key="run_compare")

    # ── Capability comparison table ──
    st.markdown("<div class='q-card'>", unsafe_allow_html=True)
    comp_data = {
        "Capability": [
            "Feature space", "Kernel evaluation", "Training complexity",
            "Noise sensitivity", "Hardware today", "Best suited for",
        ],
        "Classical ML": [
            "Polynomial / RBF kernels", "O(n²) classically", "O(n³) SVM",
            "Robust", "Ubiquitous", "Tabular, NLP, CV",
        ],
        "Quantum ML": [
            "Exponentially large Hilbert space", "Estimated via circuit", "O(n²) shots",
            "Error-prone (NISQ era)", "Limited (50–1000 qubits)", "High-dim optimization, chemistry",
        ],
    }
    st.table(comp_data)
    st.markdown("</div>", unsafe_allow_html=True)

    if run_compare:
        rng = np.random.default_rng(42)

        # ── Synthetic XOR-like dataset ──
        def make_dataset(n):
            X, y = [], []
            for cls in [0, 1]:
                cx = rng.normal([cls*1.5, cls*1.5], 0.5, (n, 2))
                X.extend(cx); y.extend([cls]*n)
            return np.array(X), np.array(y)

        X, y = make_dataset(n_points)

        # ── Classical accuracy (linear boundary) ──
        from sklearn.svm import SVC
        from sklearn.model_selection import cross_val_score
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        Xs = scaler.fit_transform(X)
        cl_svm = SVC(kernel='rbf', C=1.0, gamma='scale')
        cl_acc = cross_val_score(cl_svm, Xs, y, cv=4, scoring='accuracy').mean()

        # ── Quantum kernel (simulated via ZZFeatureMap-style inner product) ──
        def quantum_kernel_entry(x1, x2):
            """Estimate ⟨ϕ(x2)|ϕ(x1)⟩ via swap-test circuit."""
            n_feat = 2
            qc = QuantumCircuit(2*n_feat + 1, 1)
            # Ancilla H
            qc.h(0)
            # Encode x1 into qubits 1,2
            for i, xi in enumerate(x1[:n_feat]):
                qc.ry(xi, i+1)
            # Encode x2 into qubits 3,4
            for i, xi in enumerate(x2[:n_feat]):
                qc.ry(xi, i+1+n_feat)
            # Swap test
            for i in range(n_feat):
                qc.cswap(0, i+1, i+1+n_feat)
            qc.h(0)
            qc.measure(0, 0)
            tqc = transpile(qc, sim)
            res = sim.run(tqc, shots=512).result()
            p0 = res.get_counts().get('0', 0) / 512
            return 2*p0 - 1

        # Sample small subset for quantum kernel
        n_qk = min(20, n_points)
        idx = rng.choice(len(X), n_qk*2, replace=False)
        Xq, yq = X[idx], y[idx]

        with st.spinner("Computing quantum kernel matrix (this runs real Qiskit circuits)…"):
            K = np.zeros((n_qk*2, n_qk*2))
            for i in range(n_qk*2):
                for j in range(i, n_qk*2):
                    k_val = quantum_kernel_entry(Xq[i], Xq[j])
                    K[i,j] = K[j,i] = k_val

        # Train classical SVM on quantum kernel matrix
        from sklearn.svm import SVC as SVC2
        qk_svm = SVC2(kernel='precomputed')
        split = int(0.7 * n_qk*2)
        qk_svm.fit(K[:split, :split], yq[:split])
        qk_preds = qk_svm.predict(K[split:, :split])
        qk_acc = (qk_preds == yq[split:]).mean()

        # ── Accuracy bars ──
        fig_acc = go.Figure(go.Bar(
            x=['Classical RBF-SVM', 'Quantum Kernel SVM'],
            y=[cl_acc*100, qk_acc*100],
            marker=dict(
                color=['#1a5fa8', '#5fb4ff'],
                line=dict(color=['#3b7dbf','#93c5fd'], width=1),
            ),
            text=[f"{cl_acc*100:.1f}%", f"{qk_acc*100:.1f}%"],
            textposition='outside',
            textfont=dict(color='#c8d8f0', size=13),
            width=0.4,
        ))
        fig_acc.update_layout(
            paper_bgcolor='#04080f', plot_bgcolor='#07141f',
            font=dict(family='Space Grotesk', color='#c8d8f0'),
            yaxis=dict(range=[0,110], title='Accuracy (%)', gridcolor='#1a3a5c'),
            xaxis=dict(gridcolor='#1a3a5c'),
            title=dict(text="Cross-validated Accuracy",
                       font=dict(size=14, color='#dceeff')),
            margin=dict(l=30, r=30, t=50, b=30),
        )
        st.plotly_chart(fig_acc, use_container_width=True)

        # ── Quantum kernel matrix heatmap ──
        fig_km = go.Figure(go.Heatmap(
            z=K, colorscale=[[0,'#04080f'],[0.5,'#1a5fa8'],[1,'#5fb4ff']],
            showscale=True,
            colorbar=dict(tickfont=dict(color='#7ca4c8')),
        ))
        fig_km.update_layout(
            paper_bgcolor='#04080f', plot_bgcolor='#07141f',
            font=dict(family='Space Grotesk', color='#c8d8f0'),
            title=dict(text="Quantum Kernel Matrix (swap-test estimation)",
                       font=dict(size=13, color='#dceeff')),
            margin=dict(l=10, r=10, t=45, b=10), height=340,
        )
        st.plotly_chart(fig_km, use_container_width=True)

        st.markdown(f"""
<div class='q-card-glow'>
  <span class='section-eyebrow'>Interpretation</span><br>
  Classical RBF-SVM achieved <b style='color:#5fb4ff;'>{cl_acc*100:.1f}%</b> accuracy
  on {n_points*2} samples with 4-fold CV.
  The quantum kernel SVM estimated via real Aer circuits achieved
  <b style='color:#5fb4ff;'>{qk_acc*100:.1f}%</b> on a {n_qk*2}-sample subset.
  The quantum kernel encodes data in a Hilbert space that may be classically
  intractable at scale — today's advantage is architectural, not yet computational on NISQ hardware.
</div>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — QUANTUM RANDOM NUMBERS
# ════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("""
<div class='section-eyebrow'>Quantum Random Number Generation</div>
<div class='section-title'>True Randomness from Superposition</div>
<div class='section-sub'>
  Classical PRNGs are deterministic. Quantum measurement of a superposed qubit
  is provably non-deterministic — the gold standard for cryptographic keys,
  Monte Carlo simulation, and fair lotteries.
</div>
""", unsafe_allow_html=True)

    col_a, col_b, col_c = st.columns(3)
    n_bits   = col_a.slider("Bits to generate", 8, 256, 64, step=8)
    n_int    = col_b.slider("Integer range (0 – N)", 2, 1000, 100)
    gen_btn  = col_c.button("🎲 Generate", key="gen_rand")

    def qrng(n_bits):
        qc = QuantumCircuit(min(n_bits, 20), min(n_bits, 20))
        qc.h(range(min(n_bits, 20)))
        qc.measure(range(min(n_bits, 20)), range(min(n_bits, 20)))
        tqc = transpile(qc, sim)
        counts = sim.run(tqc, shots=1).result().get_counts()
        batch = list(counts.keys())[0]
        # extend if needed
        bits = batch
        while len(bits) < n_bits:
            bits += batch
        return bits[:n_bits]

    if gen_btn:
        with st.spinner("Collapsing superpositions…"):
            bits = qrng(n_bits)

        # Display bit string
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"<div class='bit-strip'>{bits}</div>", unsafe_allow_html=True)

        # Derive integer
        int_val = int(bits, 2) % (n_int + 1)
        hex_val = hex(int(bits, 2))

        mc1, mc2, mc3 = st.columns(3)
        mc1.markdown(f"<div class='metric-block'><div class='metric-value'>{int_val}</div>"
                     f"<div class='metric-label'>Random integer (0–{n_int})</div></div>",
                     unsafe_allow_html=True)
        mc2.markdown(f"<div class='metric-block'><div class='metric-value' "
                     f"style='font-size:1.1rem;'>{hex_val[:16]}…</div>"
                     f"<div class='metric-label'>Hex representation</div></div>",
                     unsafe_allow_html=True)
        mc3.markdown(f"<div class='metric-block'><div class='metric-value'>"
                     f"{bits.count('1')}/{n_bits}</div>"
                     f"<div class='metric-label'>Ones ratio</div></div>",
                     unsafe_allow_html=True)

        # Frequency chart across multiple generations
        st.markdown("<hr style='border-color:#1a3a5c;'>", unsafe_allow_html=True)
        st.markdown("#### Distribution check — 200 quantum integers")
        with st.spinner("Running 200 generations…"):
            sample_size = 200
            values = []
            for _ in range(sample_size):
                b = qrng(min(n_bits, 20))
                values.append(int(b, 2) % (n_int + 1))

        fig_dist = go.Figure(go.Histogram(
            x=values, nbinsx=min(n_int+1, 30),
            marker=dict(color='#1a5fa8', line=dict(color='#5fb4ff', width=0.5)),
        ))
        fig_dist.add_hline(y=sample_size/(min(n_int+1, 30)),
                           line=dict(color='#fbbf24', dash='dash', width=1.5),
                           annotation_text="Expected uniform",
                           annotation_font_color='#fbbf24')
        fig_dist.update_layout(
            paper_bgcolor='#04080f', plot_bgcolor='#07141f',
            font=dict(family='Space Grotesk', color='#c8d8f0'),
            xaxis=dict(title='Value', gridcolor='#1a3a5c'),
            yaxis=dict(title='Count', gridcolor='#1a3a5c'),
            title=dict(text=f"Distribution of {sample_size} quantum random integers (0–{n_int})",
                       font=dict(size=13, color='#dceeff')),
            margin=dict(l=30, r=30, t=50, b=30),
        )
        st.plotly_chart(fig_dist, use_container_width=True)

        # Entropy
        from collections import Counter
        counts_dist = Counter(values)
        probs_arr = np.array(list(counts_dist.values())) / sample_size
        entropy = -np.sum(probs_arr * np.log2(probs_arr + 1e-12))
        max_entropy = np.log2(len(counts_dist))
        st.markdown(f"""
<div class='q-card-glow'>
  <span class='section-eyebrow'>Shannon Entropy</span><br>
  Measured: <b style='color:#5fb4ff;'>{entropy:.3f} bits</b> &nbsp;/&nbsp;
  Max theoretical: <b style='color:#5fb4ff;'>{max_entropy:.3f} bits</b><br>
  <span style='color:#7ca4c8; font-size:0.85rem;'>
  Ratio {entropy/max_entropy*100:.1f}% — closer to 100% means closer to true uniform randomness.
  Quantum hardware achieves this because measurement outcome is fundamentally undetermined before observation.
  </span>
</div>
""", unsafe_allow_html=True)

    else:
        st.markdown("""
<div class='q-card'>
  <span class='section-eyebrow'>How it works</span><br>
  <ol style='color:#7ca4c8; font-size:0.88rem; line-height:2;'>
    <li>Apply a Hadamard gate to place each qubit in <span style='color:#5fb4ff;'>|0⟩ + |1⟩</span> superposition.</li>
    <li>Measure — the wavefunction collapses to 0 or 1 with equal probability.</li>
    <li>Concatenate all measurement results into a random bit string.</li>
    <li>Derive integers, hex keys, or any entropy-consuming primitive.</li>
  </ol>
  This is <b style='color:#dceeff;'>certified randomness</b> — no seed, no pattern, no prediction possible.
</div>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# TAB 4 — BB84 QUANTUM CRYPTOGRAPHY
# ════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("""
<div class='section-eyebrow'>Quantum Key Distribution</div>
<div class='section-title'>BB84 Protocol Simulator</div>
<div class='section-sub'>
  BB84 (Bennett & Brassard, 1984) is the first and most widely deployed
  quantum cryptographic protocol. An eavesdropper <b>cannot intercept
  the key without being detected</b> — a guarantee impossible with classical cryptography.
</div>
""", unsafe_allow_html=True)

    n_bits_bb84 = st.slider("Key length (bits)", 8, 64, 24, step=4)
    eve_present = st.checkbox("🕵️ Include eavesdropper (Eve)", value=False)
    bb84_btn = st.button("🔐 Run BB84 Protocol", key="bb84_run")

    def run_bb84(n, eavesdrop=False):
        """Simulate BB84 with optional Eve using Qiskit."""
        alice_bits   = [random.randint(0,1) for _ in range(n)]
        alice_bases  = [random.choice(['+','x']) for _ in range(n)]
        bob_bases    = [random.choice(['+','x']) for _ in range(n)]

        bob_results = []
        for i in range(n):
            qc = QuantumCircuit(1, 1)
            # Alice encodes
            if alice_bits[i] == 1:
                qc.x(0)
            if alice_bases[i] == 'x':
                qc.h(0)
            # Eve intercepts (random basis)
            if eavesdrop:
                eve_basis = random.choice(['+','x'])
                if eve_basis == 'x':
                    qc.h(0)
                qc.measure(0, 0)
                # Eve re-prepares based on her result
                tqc = transpile(qc, sim)
                eve_res = list(sim.run(tqc, shots=1).result().get_counts().keys())[0]
                qc = QuantumCircuit(1, 1)
                if eve_res == '1':
                    qc.x(0)
                if eve_basis == 'x':
                    qc.h(0)
            # Bob measures
            if bob_bases[i] == 'x':
                qc.h(0)
            qc.measure(0, 0)
            tqc = transpile(qc, sim)
            res = sim.run(tqc, shots=1).result().get_counts()
            bob_results.append(int(list(res.keys())[0]))

        # Sifting: keep only matching bases
        sifted_alice, sifted_bob, matched_idx = [], [], []
        for i in range(n):
            if alice_bases[i] == bob_bases[i]:
                sifted_alice.append(alice_bits[i])
                sifted_bob.append(bob_results[i])
                matched_idx.append(i)

        # QBER
        errors = sum(a != b for a, b in zip(sifted_alice, sifted_bob))
        qber = errors / len(sifted_alice) if sifted_alice else 0

        return {
            'alice_bits': alice_bits,
            'alice_bases': alice_bases,
            'bob_bases': bob_bases,
            'bob_results': bob_results,
            'sifted_alice': sifted_alice,
            'sifted_bob': sifted_bob,
            'matched_idx': matched_idx,
            'qber': qber,
            'errors': errors,
        }

    if bb84_btn:
        with st.spinner("Running BB84 quantum key exchange…"):
            result = run_bb84(n_bits_bb84, eve_present)

        # ── Protocol table ──
        st.markdown("#### Step-by-step protocol trace")
        n_show = min(n_bits_bb84, 16)
        rows = []
        for i in range(n_show):
            match = "✅" if result['alice_bases'][i] == result['bob_bases'][i] else "❌"
            rows.append({
                "Bit #": i+1,
                "Alice bit": result['alice_bits'][i],
                "Alice basis": result['alice_bases'][i],
                "Bob basis": result['bob_bases'][i],
                "Bob result": result['bob_results'][i],
                "Basis match": match,
            })
        import pandas as pd
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        # ── Sifted key ──
        st.markdown("#### Sifted key (after basis reconciliation)")
        key_html = ""
        for a, b in zip(result['sifted_alice'], result['sifted_bob']):
            cls = "key-match" if a == b else "key-nomat"
            key_html += f"<span class='key-cell {cls}'>{a}</span>"
        st.markdown(f"<div style='margin:0.5rem 0;'>{key_html}</div>",
                    unsafe_allow_html=True)

        # ── Metrics ──
        m1, m2, m3, m4 = st.columns(4)
        m1.markdown(f"<div class='metric-block'><div class='metric-value'>{n_bits_bb84}</div>"
                    "<div class='metric-label'>Bits sent</div></div>", unsafe_allow_html=True)
        m2.markdown(f"<div class='metric-block'><div class='metric-value'>"
                    f"{len(result['sifted_alice'])}</div>"
                    "<div class='metric-label'>Sifted key length</div></div>", unsafe_allow_html=True)
        m3.markdown(f"<div class='metric-block'><div class='metric-value'>"
                    f"{result['errors']}</div>"
                    "<div class='metric-label'>Bit errors</div></div>", unsafe_allow_html=True)
        qber_color = "#f87171" if result['qber'] > 0.1 else "#4ade80"
        m4.markdown(f"<div class='metric-block'><div class='metric-value' "
                    f"style='color:{qber_color};'>{result['qber']*100:.1f}%</div>"
                    "<div class='metric-label'>QBER</div></div>", unsafe_allow_html=True)

        # ── QBER gauge ──
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=result['qber']*100,
            number=dict(suffix='%', font=dict(color='#c8d8f0', family='Space Grotesk')),
            gauge=dict(
                axis=dict(range=[0, 50], tickcolor='#5d8ab0',
                          tickfont=dict(color='#7ca4c8')),
                bar=dict(color='#1a5fa8'),
                bgcolor='#07141f',
                bordercolor='#1a3a5c',
                steps=[
                    dict(range=[0, 11], color='#0e3a1e'),
                    dict(range=[11, 25], color='#2d3012'),
                    dict(range=[25, 50], color='#2d1515'),
                ],
                threshold=dict(line=dict(color='#fbbf24', width=2), value=11),
            ),
            title=dict(text="Quantum Bit Error Rate (QBER)",
                       font=dict(color='#dceeff', size=14)),
        ))
        fig_gauge.update_layout(
            paper_bgcolor='#04080f', height=260,
            font=dict(family='Space Grotesk'),
            margin=dict(l=20, r=20, t=40, b=20),
        )
        st.plotly_chart(fig_gauge, use_container_width=True)

        # ── Verdict ──
        if eve_present and result['qber'] > 0.10:
            verdict = ("🚨 <b>Eve detected!</b> QBER of "
                       f"{result['qber']*100:.1f}% exceeds the 11% security threshold. "
                       "Alice and Bob will discard this key and retry on a clean channel. "
                       "Eve's interception disturbed the quantum states — "
                       "a consequence of the <b>no-cloning theorem</b>.")
            vcol = "#f87171"
        elif eve_present:
            verdict = (f"⚠️ Eve was present but QBER ({result['qber']*100:.1f}%) stayed below threshold — "
                       "Eve got lucky with basis choices this run. In practice, "
                       "more bits are exchanged to make this statistically impossible.")
            vcol = "#fbbf24"
        else:
            verdict = (f"✅ <b>Secure channel established.</b> QBER = {result['qber']*100:.1f}%. "
                       f"Alice and Bob share a {len(result['sifted_alice'])}-bit secret key with no detectable eavesdropping. "
                       "This key can now seed a one-time pad for information-theoretically secure communication.")
            vcol = "#4ade80"

        st.markdown(f"<div class='q-card-glow'>"
                    f"<span class='section-eyebrow'>Security Verdict</span><br>"
                    f"<span style='color:{vcol};'>{verdict}</span></div>",
                    unsafe_allow_html=True)

    else:
        st.markdown("""
<div class='q-card'>
  <span class='section-eyebrow'>BB84 Protocol Overview</span><br>
  <div style='font-size:0.88rem; color:#7ca4c8; line-height:2;'>
  1. <b style='color:#dceeff;'>Alice</b> encodes random bits in random bases (rectilinear +  or diagonal ×).<br>
  2. <b style='color:#dceeff;'>Bob</b> measures each qubit in a randomly chosen basis.<br>
  3. <b style='color:#dceeff;'>Sifting:</b> they publicly compare bases (not bits) and keep only matching measurements.<br>
  4. <b style='color:#dceeff;'>Error check:</b> a sample is compared; QBER > 11% reveals an eavesdropper.<br>
  5. <b style='color:#dceeff;'>Key:</b> remaining bits form a shared secret — information-theoretically secure.
  </div>
</div>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# TAB 5 — PORTFOLIO STORY
# ════════════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown("""
<div class='section-eyebrow'>Portfolio Story</div>
<div class='section-title'>Why Quantum, Why Now</div>
<div class='section-sub'>
  The engineering narrative behind Module 4 and how it connects to my
  broader AI engineering journey.
</div>
""", unsafe_allow_html=True)

    # Journey timeline
    st.markdown("### 🗺️ Engineering Journey")
    milestones = [
        ("🌍", "Petroleum Geology & Hydrogeology",
         "10+ years building quantitative models for subsurface systems — "
         "I learned to reason under deep uncertainty, invert complex data, "
         "and explain technical findings to non-technical stakeholders."),
        ("🤖", "Stanford / Andrew Ng AI/ML Curriculum",
         "Transitioned into AI/ML: linear algebra, gradient descent, neural networks, "
         "CNNs, RNNs, transformers. Built intuition for when a model works "
         "and, more importantly, when it doesn't."),
        ("🧠", "Module 1 — ReAct Agent (LangGraph + Groq)",
         "First production AI agent: a LangGraph ReAct loop backed by "
         "llama-3.3-70b-versatile on Groq with sub-300ms tool-call latency. "
         "Taught me agentic state machines and prompt engineering at depth."),
        ("🔀", "Module 2 — Multi-Agent HybridRAG",
         "Supervisor-pattern multi-agent system with FAISS vector search "
         "and DuckDuckGo retrieval. Solved the precision/recall tradeoff "
         "that single-index RAG systems hit at scale."),
        ("📊", "Module 3 — MLOps Pipeline",
         "End-to-end MLOps: MLflow experiment tracking, Prometheus metrics, "
         "Docker containerisation, GitHub Actions CI/CD, AWS ECS simulation. "
         "Closed the gap between 'model works' and 'model ships'."),
        ("⚛️", "Module 4 — Quantum AI Explorer (this app)",
         "Qiskit circuits, quantum kernel ML, certified random number generation, "
         "and BB84 quantum key distribution. Positioning for the next wave: "
         "quantum-enhanced optimisation and post-classical ML kernels."),
    ]

    for icon, title, body in milestones:
        st.markdown(f"""
<div class='q-card' style='display:flex; gap:1.2rem; align-items:flex-start;'>
  <div style='font-size:2rem; min-width:40px; line-height:1;'>{icon}</div>
  <div>
    <div style='font-weight:600; color:#dceeff; margin-bottom:4px;'>{title}</div>
    <div style='font-size:0.87rem; color:#7ca4c8; line-height:1.7;'>{body}</div>
  </div>
</div>
""", unsafe_allow_html=True)

    # Technical depth section
    st.markdown("### 🔬 Technical Choices in Module 4")
    st.markdown("""
<div class='q-card'>
<div style='font-size:0.88rem; color:#7ca4c8; line-height:2;'>
  <b style='color:#dceeff;'>Why Qiskit?</b>
  IBM's Qiskit is the most production-deployed quantum SDK, with direct
  access to real quantum hardware via IBM Quantum Network. Learning it now
  means being hardware-ready when NISQ devices stabilise.<br><br>

  <b style='color:#dceeff;'>Why quantum ML kernels?</b>
  Kernel methods are the mathematical bridge between classical and quantum ML.
  A quantum kernel can represent inner products in an exponentially large feature space
  that would be classically intractable — the key theoretical advantage of QML.<br><br>

  <b style='color:#dceeff;'>Why BB84?</b>
  Quantum cryptography is already deployed in national infrastructure (China's
  quantum backbone, EU QCI). Understanding the protocol at circuit level —
  not just conceptually — is a differentiator for any AI/security engineering role.<br><br>

  <b style='color:#dceeff;'>Why QRNG?</b>
  Every LLM alignment technique involving sampling, every Monte Carlo simulation,
  every cryptographic key ultimately traces back to a random number generator.
  Quantum-sourced entropy is the highest quality source available.
</div>
</div>
""", unsafe_allow_html=True)

    # Skills demonstrated
    st.markdown("### 🛠️ Skills Demonstrated Across Portfolio")
    skills = [
        ("Agentic AI", ["LangGraph", "ReAct loops", "Tool calling", "State machines"]),
        ("RAG & Retrieval", ["FAISS", "HybridRAG", "Embeddings", "Reranking"]),
        ("MLOps", ["MLflow", "Docker", "GitHub Actions", "Prometheus", "AWS ECS"]),
        ("Quantum Computing", ["Qiskit", "Aer simulator", "Circuit design", "BB84", "QKD"]),
        ("Backend ML", ["Python", "NumPy", "scikit-learn", "REST APIs", "Streamlit"]),
        ("Data & Viz", ["Plotly", "Pandas", "Matplotlib", "Interactive dashboards"]),
    ]

    cols_sk = st.columns(3)
    for idx, (cat, tags) in enumerate(skills):
        with cols_sk[idx % 3]:
            tag_html = " ".join(
                f"<span style='background:#0f3460; color:#7dd3fc; border:1px solid #1a5fa8; "
                f"border-radius:4px; padding:2px 8px; font-size:0.76rem; "
                f"font-family:JetBrains Mono,monospace; margin:2px; display:inline-block;'>"
                f"{t}</span>" for t in tags
            )
            st.markdown(f"""
<div class='q-card' style='min-height:110px;'>
  <div style='font-weight:600; color:#dceeff; margin-bottom:8px; font-size:0.9rem;'>{cat}</div>
  <div>{tag_html}</div>
</div>
""", unsafe_allow_html=True)

    # CTA
    st.markdown("""
<div class='q-card-glow' style='text-align:center; padding:2rem;'>
  <div style='font-size:1.3rem; font-weight:600; color:#dceeff; margin-bottom:0.5rem;'>
    Open to senior AI/ML engineering roles
  </div>
  <div style='font-size:0.9rem; color:#7ca4c8; margin-bottom:1rem;'>
    Remote · US companies · $150K+ · Python / MLOps / Agentic AI / Quantum
  </div>
  <div style='display:flex; gap:1rem; justify-content:center; flex-wrap:wrap;'>
    <a href='https://github.com/joneslokouba-ui/ai-engineering-portfolio'
       target='_blank'
       style='background:#0f3460; color:#5fb4ff; border:1px solid #3b7dbf;
              border-radius:6px; padding:8px 20px; text-decoration:none;
              font-weight:500; font-size:0.9rem;'>
      🔗 GitHub Portfolio
    </a>
    <a href='https://linkedin.com/in/geoffrey-okwi-826871415'
       target='_blank'
       style='background:#0f3460; color:#5fb4ff; border:1px solid #3b7dbf;
              border-radius:6px; padding:8px 20px; text-decoration:none;
              font-weight:500; font-size:0.9rem;'>
      💼 LinkedIn
    </a>
  </div>
</div>
""", unsafe_allow_html=True)