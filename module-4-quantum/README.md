# ⚛️ Module 4 — Quantum AI Explorer

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://module4-quantum.streamlit.app)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![Qiskit](https://img.shields.io/badge/Qiskit-1.4.2-6929C4?style=flat&logo=ibm&logoColor=white)](https://qiskit.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Part of the [AI Engineering Portfolio](https://github.com/joneslokouba-ui/ai-engineering-portfolio)**
> by Geoffrey Jones Okwi — AI/ML Engineer · Calgary, AB

---

## 🔬 Overview

A hands-on quantum computing explorer built with **Qiskit 1.4.x** and **Streamlit**.
Covers five production-relevant quantum topics: circuit simulation, quantum kernel ML,
certified random number generation, quantum cryptography, and an engineering narrative
connecting quantum to the broader AI/ML stack.

---

## 🗂️ Tabs

| Tab | What it does |
|-----|-------------|
| ⚡ **Quantum Circuits** | Build & simulate Bell, GHZ, Superposition, QFT, Grover circuits with live Plotly histograms and a Bloch sphere |
| 🤖 **Classical vs Quantum ML** | Quantum kernel SVM (swap-test estimation) vs classical RBF-SVM on a synthetic dataset |
| 🎲 **Quantum Random Numbers** | True QRNG from qubit superposition — bit strings, integers, hex keys, Shannon entropy |
| 🔐 **BB84 Cryptography** | Full BB84 quantum key distribution with optional Eve eavesdropper and QBER gauge |
| 📖 **Portfolio Story** | Engineering journey, technical choices, skills map, recruiter CTA |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Quantum runtime | Qiskit 1.4.2 + Qiskit-Aer 0.15.1 |
| Frontend | Streamlit 1.45.1 |
| Visualisation | Plotly 6.x · Matplotlib 3.10 |
| ML | scikit-learn 1.6 (quantum kernel SVM) |
| Language | Python 3.11 |

---

## 🚀 Run Locally

```bash
# 1. Clone the portfolio
git clone https://github.com/joneslokouba-ui/ai-engineering-portfolio.git
cd ai-engineering-portfolio/module-4-quantum

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch
streamlit run app.py
```

---

## 📐 Architecture

```
module-4-quantum/
├── app.py                  # Main Streamlit app — 5 tabs, ~600 lines
├── requirements.txt        # Pinned dependencies for Streamlit Cloud
├── README.md               # This file
└── .streamlit/
    └── config.toml         # Dark quantum theme
```

---

## 🧠 Key Concepts Demonstrated

- **Quantum gate composition** — Hadamard, CNOT, CZ, CP, SWAP, Toffoli
- **Quantum Fourier Transform** — backbone of Shor's algorithm
- **Grover's algorithm** — quadratic speedup for unstructured search
- **Quantum kernel methods** — swap-test inner product estimation in Hilbert space
- **QRNG** — certified randomness from wavefunction collapse
- **BB84 protocol** — no-cloning theorem, QBER, basis reconciliation, eavesdropper detection

---

## 🗺️ Full Portfolio

| Module | Description | Live App |
|--------|-------------|----------|
| [Module 1](../module-1-ai-agents/) | ReAct Agent — LangGraph + Groq (llama-3.3-70b) | [module1-ai-agents.streamlit.app](https://module1-ai-agents.streamlit.app) |
| [Module 2](../module-2-multi-agent/) | Multi-Agent HybridRAG — FAISS + DuckDuckGo | [module2-multi-agent.streamlit.app](https://module2-multi-agent.streamlit.app) |
| [Module 3](../module-3-mlops/) | MLOps Pipeline — MLflow + Docker + GitHub Actions | [module3-mlops.streamlit.app](https://module3-mlops.streamlit.app) |
| **Module 4** | **Quantum AI Explorer — Qiskit + BB84 + QRNG** | [module4-quantum.streamlit.app](https://module4-quantum.streamlit.app) |

---

## 👤 Author

**Geoffrey Jones Okwi** — AI/ML Engineer  
MSc Earth Sciences · University of Waterloo  
Stanford / Andrew Ng AI/ML Curriculum  
10+ years consulting · Petroleum Geology & Hydrogeology

🔗 [GitHub Portfolio](https://github.com/joneslokouba-ui/ai-engineering-portfolio)  
💼 [LinkedIn](https://linkedin.com/in/geoffrey-okwi-826871415)

> *Open to senior remote AI/ML engineering roles with US companies · $150K+*