"""
Module 1: AI Agent — Streamlit Frontend
Author: Geoffrey Jones Okwi
FIXES: chat bubble visibility + tool_use_failed error
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage
from agent.agent_core import run_agent

# ─── Page config ───────────────────────────────────────────
st.set_page_config(
    page_title="Production AI Agent | Geoffrey Okwi",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ────────────────────────────────────────────
st.markdown("""
<style>
    /* App background */
    .stApp { background-color: #0a0f1e; color: #e2e8f0; }

    /* Header card */
    .agent-header {
        background: linear-gradient(135deg, #1a1f3a 0%, #0d1117 100%);
        border: 1px solid #2d3748;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 24px;
    }
    .agent-header h1 { color: #63b3ed; margin: 0; font-size: 1.8rem; }
    .agent-header p  { color: #a0aec0; margin: 4px 0 0; }

    /* Metric cards */
    .metric-card {
        background: #1a1f3a;
        border: 1px solid #2d3748;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
    }
    .metric-card .value { font-size: 1.8rem; font-weight: bold; color: #63b3ed; }
    .metric-card .label { font-size: 0.8rem; color: #718096; }

    /* ── CHAT BUBBLE FIXES ── */
    /* User bubble — bright white text on blue */
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
        background-color: #1a365d !important;
        border-radius: 12px;
        padding: 12px 16px;
        margin: 8px 0;
    }
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) p,
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) div {
        color: #ffffff !important;
    }

    /* Assistant bubble — bright white text on dark green-tinted */
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
        background-color: #1a2e1a !important;
        border: 1px solid #2d5a27;
        border-radius: 12px;
        padding: 12px 16px;
        margin: 8px 0;
    }
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) p,
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) div {
        color: #e2fce2 !important;
    }

    /* Fallback: force ALL chat text to be visible */
    [data-testid="stChatMessage"] * {
        color: #f0f4f8 !important;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #0d1117;
        border-right: 1px solid #2d3748;
    }
    [data-testid="stSidebar"] * { color: #e2e8f0 !important; }

    /* Input box */
    [data-testid="stChatInputTextArea"] {
        background-color: #1a1f3a !important;
        color: #ffffff !important;
        border: 1px solid #4a5568;
    }
</style>
""", unsafe_allow_html=True)

# ─── Sidebar ───────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🛠 Agent Config")
    st.selectbox("Model", ["llama-3.3-70b-versatile"], index=0)
    st.slider("Temperature", 0.0, 1.0, 0.1, 0.05)
    st.slider("Max Iterations", 3, 15, 10)

    st.markdown("---")
    st.markdown("### 🧰 Available Tools")
    tools_info = {
        "🔍 Web Search":  "Real-time information lookup",
        "🧮 Calculator":   "Safe math expression evaluator",
        "📊 Job Market":   "AI/ML role market data",
    }
    for name, desc in tools_info.items():
        st.markdown(f"**{name}**  \n{desc}")

    st.markdown("---")
    st.markdown("### 📦 Stack")
    st.caption("LangChain · LangGraph · Groq · Streamlit")
    st.caption("llama-3.3-70b-versatile")

    if st.button("🗑 Clear History", use_container_width=True):
        st.session_state.messages = []
        st.session_state.lc_history = []
        st.rerun()

# ─── Header ────────────────────────────────────────────────
st.markdown("""
<div class="agent-header">
    <h1>🤖 Production AI Agent — Module 1</h1>
    <p>Geoffrey Jones Okwi · AI/ML Engineer · LangChain + LangGraph</p>
</div>
""", unsafe_allow_html=True)

# ─── Metrics ───────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown('<div class="metric-card"><div class="value">3</div><div class="label">Tools Active</div></div>', unsafe_allow_html=True)
with col2:
    turns = len(st.session_state.get("messages", [])) // 2
    st.markdown(f'<div class="metric-card"><div class="value">{turns}</div><div class="label">Turns</div></div>', unsafe_allow_html=True)
with col3:
    st.markdown('<div class="metric-card"><div class="value">ReAct</div><div class="label">Loop Type</div></div>', unsafe_allow_html=True)
with col4:
    st.markdown('<div class="metric-card"><div class="value">✅</div><div class="label">Agent Live</div></div>', unsafe_allow_html=True)

st.markdown("---")

# ─── Session state ─────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "lc_history" not in st.session_state:
    st.session_state.lc_history = []

# ─── Chat history ──────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ─── Quick-start prompts ───────────────────────────────────
if not st.session_state.messages:
    st.markdown("#### 💡 Try these:")
    cols = st.columns(3)
    prompts = [
        "What skills do I need for an AI Engineer role?",
        "Calculate: (150000 * 0.15) + 5000",
        "Job market data for AI Consultant",
    ]
    for i, p in enumerate(prompts):
        if cols[i].button(p, use_container_width=True):
            st.session_state.pending_prompt = p
            st.rerun()

# Handle quick-start click
if "pending_prompt" in st.session_state:
    user_input = st.session_state.pop("pending_prompt")
else:
    user_input = st.chat_input("Ask the agent anything…")

# ─── Agent call ────────────────────────────────────────────
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("🤖 Agent thinking…"):
            try:
                result = run_agent(user_input, history=st.session_state.lc_history)
                answer = result["answer"]

                # Handle list content (Groq sometimes returns list)
                if isinstance(answer, list):
                    answer = " ".join(
                        block.get("text", "") if isinstance(block, dict) else str(block)
                        for block in answer
                    )

                st.session_state.lc_history.append(HumanMessage(content=user_input))
                st.session_state.lc_history.append(AIMessage(content=answer))

                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})

            except Exception as e:
                err = f"⚠️ Agent error: {str(e)}"
                st.error(err)
                st.session_state.messages.append({"role": "assistant", "content": err})