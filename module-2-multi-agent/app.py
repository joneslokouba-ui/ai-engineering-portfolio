"""
Module 2: Multi-Agent System — Streamlit Frontend
Author: Geoffrey Jones Okwi | AI/ML Engineer
Upgrade: Shows which agent handled each query
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage
from graph.multi_agent_graph import run_multi_agent

# ─── Page config ───────────────────────────────────────────
st.set_page_config(
    page_title="Multi-Agent System | Geoffrey Okwi",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ───────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #0a0f1e; color: #e2e8f0; }

    .main-header {
        background: linear-gradient(135deg, #1a1f3a 0%, #0d1117 100%);
        border: 1px solid #2d3748;
        border-left: 4px solid #63b3ed;
        border-radius: 12px;
        padding: 24px 28px;
        margin-bottom: 24px;
    }
    .main-header h1 { color: #63b3ed; margin: 0; font-size: 1.8rem; }
    .main-header p  { color: #a0aec0; margin: 6px 0 0; font-size: 0.95rem; }

    /* Agent route badge */
    .agent-badge {
        display: inline-block;
        padding: 3px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: bold;
        margin-bottom: 6px;
    }
    .badge-researcher { background:#1a365d; color:#90cdf4; border:1px solid #2b6cb0; }
    .badge-analyst    { background:#1a2f1a; color:#9ae6b4; border:1px solid #276749; }
    .badge-rag_agent  { background:#2d1a4a; color:#d6bcfa; border:1px solid #6b46c1; }
    .badge-supervisor { background:#2d2a1a; color:#fbd38d; border:1px solid #b7791f; }

    /* Metric cards */
    .metric-card {
        background:#1a1f3a; border:1px solid #2d3748;
        border-radius:8px; padding:16px; text-align:center;
    }
    .metric-card .value { font-size:1.8rem; font-weight:bold; color:#63b3ed; }
    .metric-card .label { font-size:0.8rem; color:#718096; }

    /* Chat bubbles */
    [data-testid="stChatMessage"] * { color: #f0f4f8 !important; }

    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
        background-color:#1a365d !important;
        border-radius:12px; padding:12px 16px; margin:8px 0;
    }
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
        background-color:#1a2e1a !important;
        border:1px solid #2d5a27;
        border-radius:12px; padding:12px 16px; margin:8px 0;
    }

    /* Sidebar */
    [data-testid="stSidebar"] { background-color:#0d1117; border-right:1px solid #2d3748; }
    [data-testid="stSidebar"] * { color:#e2e8f0 !important; }

    /* Agent flow diagram */
    .flow-box {
        background:#1a1f3a; border:1px solid #4a5568;
        border-radius:8px; padding:12px; text-align:center;
        font-size:0.85rem; color:#e2e8f0;
    }
    .flow-arrow { text-align:center; color:#718096; font-size:1.2rem; }
</style>
""", unsafe_allow_html=True)

# ─── Agent badge helper ────────────────────────────────────
AGENT_LABELS = {
    "researcher": ("🔍", "Researcher",  "badge-researcher"),
    "analyst":    ("📊", "Analyst",     "badge-analyst"),
    "rag_agent":  ("📚", "RAG Agent",   "badge-rag_agent"),
    "supervisor": ("🧠", "Supervisor",  "badge-supervisor"),
}

def render_agent_badge(agent_name: str) -> str:
    icon, label, css = AGENT_LABELS.get(agent_name, ("🤖", agent_name, "badge-supervisor"))
    return f'<span class="agent-badge {css}">{icon} {label}</span>'


# ─── Sidebar ───────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🧠 Multi-Agent System")
    st.markdown("**Module 2** — Supervisor Pattern")
    st.markdown("---")

    st.markdown("### 🤖 Agent Team")
    st.markdown("**🧠 Supervisor**  \nRoutes tasks to specialists")
    st.markdown("**🔍 Researcher**  \nTavily web search")
    st.markdown("**📊 Analyst**  \nSalary + skill gap analysis")
    st.markdown("**📚 RAG Agent**  \nDocument search (HybridRAG)")
    st.markdown("**✍️ Synthesizer**  \nComposes final answers")

    st.markdown("---")
    st.markdown("### 📦 Stack")
    st.caption("LangChain · LangGraph · Groq")
    st.caption("Tavily · FAISS · HuggingFace")
    st.caption("llama-3.3-70b-versatile")

    st.markdown("---")
    if st.button("🗑 Clear History", use_container_width=True):
        st.session_state.messages = []
        st.session_state.lc_history = []
        st.rerun()

# ─── Header ────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🧠 Multi-Agent System — Module 2</h1>
    <p>Geoffrey Jones Okwi · AI/ML Engineer · Supervisor → Researcher | Analyst | RAG Agent</p>
</div>
""", unsafe_allow_html=True)

# ─── Metrics ───────────────────────────────────────────────
col1, col2, col3, col4, col5 = st.columns(5)
metrics = [
    ("4", "Agents"),
    (str(len(st.session_state.get("messages", [])) // 2), "Turns"),
    ("3", "Tools"),
    ("Supervisor", "Pattern"),
    ("✅", "Live"),
]
for col, (val, label) in zip([col1,col2,col3,col4,col5], metrics):
    col.markdown(
        f'<div class="metric-card"><div class="value">{val}</div>'
        f'<div class="label">{label}</div></div>',
        unsafe_allow_html=True
    )

st.markdown("---")

# ─── Session state ─────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "lc_history" not in st.session_state:
    st.session_state.lc_history = []

# ─── Chat history display ──────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg.get("agent_used"):
            badges = " ".join(render_agent_badge(a) for a in msg["agent_used"])
            st.markdown(badges, unsafe_allow_html=True)
        st.markdown(msg["content"])

# ─── Quick-start prompts ───────────────────────────────────
if not st.session_state.messages:
    st.markdown("#### 💡 Try these — watch which agent handles each:")
    prompts = [
        ("📊 Analyst",    "What is the salary for an AI Engineer with 3 years experience?"),
        ("📊 Analyst",    "My skills: Python, Docker, LangChain. Gap analysis for AI Engineer role?"),
        ("🔍 Researcher", "Search for latest LangGraph multi-agent examples 2025"),
        ("📚 RAG Agent",  "What does the document say about tax deductions?"),
        ("🧮 Calculate",  "Calculate: (150000 * 0.15) + 5000"),
        ("🧠 Direct",     "What is LangGraph and why is it used?"),
    ]
    cols = st.columns(3)
    for i, (agent_hint, p) in enumerate(prompts):
        col = cols[i % 3]
        if col.button(f"{agent_hint}\n{p[:45]}...", use_container_width=True, key=f"prompt_{i}"):
            st.session_state.pending_prompt = p
            st.rerun()

# Handle quick-start
if "pending_prompt" in st.session_state:
    user_input = st.session_state.pop("pending_prompt")
else:
    user_input = st.chat_input("Ask the multi-agent system anything…")

# ─── Run agents ────────────────────────────────────────────
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("🧠 Supervisor routing… agents working…"):
            try:
                result = run_multi_agent(user_input, history=st.session_state.lc_history)
                answer     = result["answer"]
                agent_used = result["agent_used"]

                # Show which agent handled it
                badges = " ".join(render_agent_badge(a) for a in agent_used)
                st.markdown(badges, unsafe_allow_html=True)
                st.markdown(answer)

                # Update history
                st.session_state.lc_history.append(HumanMessage(content=user_input))
                st.session_state.lc_history.append(AIMessage(content=answer))
                st.session_state.messages.append({
                    "role":       "assistant",
                    "content":    answer,
                    "agent_used": agent_used,
                })

            except Exception as e:
                err = f"⚠️ System error: {str(e)}"
                st.error(err)
                st.session_state.messages.append({"role": "assistant", "content": err, "agent_used": []})