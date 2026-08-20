# Module 10 — AEGIS: On-Chain Fraud & AML Detection Engine

Part of [`ai-engineering-portfolio`](../) — Module 10.

AEGIS is a graph-native transaction monitoring engine that detects on-chain money-laundering typologies (layering, peel chains, smurfing/structuring) using a combination of wallet clustering, graph centrality, transaction velocity, mixer proximity, and an ensemble classifier — screened against a sanctions/watchlist rule engine, and gated by a hard-coded human-adjudication requirement before any enforcement action.

**Live dashboard:** _(add Streamlit Cloud URL after deployment)_

## Why this module

Exchanges, custodians, and banks standing up crypto desks all need transaction-monitoring tooling that can keep pace with regulatory expectations (FATF Travel Rule, OFAC sanctions screening, FinCEN guidance). This module extends the real-time fraud detection architecture from **Module 6 (Sentry)** into the on-chain domain, and adopts the same **zero-autonomous-tier governance boundary** used in **Module 8 (Vigil)**: AEGIS detects, scores, and escalates — it never freezes funds, blocks transactions, or files reports on its own.

## Architecture

See [`docs/ADR-010-aegis.md`](docs/ADR-010-aegis.md) for the full architecture decision record and [`docs/architecture-diagram.mmd`](docs/architecture-diagram.mmd) for the pipeline diagram.

```
Transaction Stream → Feature Engineering → Ensemble Risk Scoring → Escalation Queue → Human Adjudication
                       (clustering, velocity,      (ML + sanctions           (Tier 3 enforcement
                        centrality, mixer prox.)     rule engine)             hard-gated)
```

## What's genuinely validated here (not just "runs without crashing")

This module surfaced and fixed three real bugs during development — each one is documented in the source comments where it was found:

1. **Wallet-clustering giant-component collapse** (`src/features/wallet_clustering.py`) — an early version of the common-input-ownership heuristic collapsed all 500 wallets into a single cluster on background traffic alone. Fixed by adding a time-window constraint.
2. **Wallet-freshness leakage** (`src/ingestion/transaction_simulator.py`) — the ensemble was trivially learning "is this wallet newly created?" instead of any real AML signal, because every laundering wallet was freshly minted while background traffic reused a fixed pool. Fixed by mixing fresh/aged wallets into both background and laundering traffic.
3. **Amount-magnitude leakage** (`src/ingestion/transaction_simulator.py`) — background and laundering transaction amounts never overlapped, so a naive dollar threshold would have "solved" detection with zero graph work. Fixed with a log-normal background distribution and overlapping laundering-case ranges.

After both fixes, the ensemble achieves **ROC-AUC 0.999** with importance spread across `cluster_size`, `mixer_proximity_score`, `degree_centrality`, and transaction amounts — not dominated by a single shortcut feature.

**End-to-end validation** (`src/simulation/discrete_event_engine.py`): across 5 independent random seeds, AEGIS achieves a **100% detection rate** on injected layering/peel-chain/smurfing cases, with a realistic ~7% false-escalation rate (not suspiciously perfect).

## Governance

`src/governance/authority_boundary.py` enforces a hard Tier 0–3 boundary:

| Tier | Action | Autonomous? |
|---|---|---|
| 0–2 | Ingest, score, populate escalation queue | Yes |
| 3 | Freeze wallet / file SAR / notify regulator | **No — `AuthorityBoundaryViolation` raised without a recorded human adjudication** |

There is no bypass parameter. This is validated in code, not just described in the ADR — see the "governance boundary self-test" panel in the dashboard's Escalation Queue tab.

## Structure

```
module-10-aegis/
├── README.md
├── docs/                    # ADR + architecture diagram
├── src/
│   ├── ingestion/           # synthetic transaction simulator
│   ├── features/            # clustering, velocity, centrality, mixer proximity
│   ├── scoring/              # ensemble classifier, sanctions matcher, composite score
│   ├── simulation/           # discrete-event validation engine
│   └── governance/           # authority boundary (Tier 0-3 enforcement gate)
├── dashboard/
│   └── streamlit_app.py
├── tests/
├── data/synthetic_ledger/
├── requirements.txt
└── pyproject.toml
```

## Running locally

```bash
pip install -r requirements.txt
streamlit run dashboard/streamlit_app.py
```

## Scope & limitations

- Transaction data is synthetic (no live on-chain data pull). A production version would integrate a chain-indexing API.
- Wallet clustering uses a simplified common-input-ownership heuristic — production-grade clustering (as used by firms like Chainalysis or Elliptic) combines dozens of proprietary heuristics.
- The composite score's explainability panel shows global feature importances plus raw feature values per wallet, not a formal per-prediction attribution method (e.g. SHAP) — a natural next iteration.