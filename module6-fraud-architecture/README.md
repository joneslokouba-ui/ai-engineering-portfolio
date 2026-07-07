# Module 6: Sentry Architecture
### System Architecture for Real-Time Fraud & Anomaly Detection

**Author:** Jones (AI/ML Engineer)
**Portfolio:** [ai-engineering-portfolio](https://github.com/joneslokouba-ui/ai-engineering-portfolio)
**Domain:** Real-time transaction fraud screening — regulated, low-latency, dual-sided error cost

---

## Why This Module Exists

Module 5 (Sentinel Architecture) proved a system design for AI whose mistakes have *physical*
consequences. This module proves the adjacent but distinct skill: designing AI systems whose
mistakes have *financial and legal* consequences — where a false positive harms a legitimate
customer and a false negative lets fraud through, and both failure directions carry real cost.

The deliverable is the same shape as Module 5: an ADR set documenting the hard architectural
decisions, diagrams, and a discrete-event simulation that proves the key decisions hold under
adversarial and degraded conditions — not a production fraud model.

---

## System Overview

```mermaid
flowchart TB
    subgraph RealTime["Real-Time Path (latency-critical)"]
        I[Ingestion Layer<br/>event stream, feature extraction]
        S[Scoring Layer<br/>fraud model / ensemble]
        D[Decision Layer<br/>thresholding: approve / decline / hold]
    end

    subgraph Oversight["Human Oversight"]
        H[Human Escalation Layer<br/>review queue, SLA-bound]
    end

    subgraph Forensics["Asynchronous — not latency-budgeted"]
        F[Forensic Attribution Layer<br/>clusters confirmed fraud cases]
        R[(Risk Registry<br/>human-confirmed entries only)]
    end

    A[Audit / Compliance Layer<br/>immutable decision log]

    I --> S --> D
    D -->|"Tier 1: reversible<br/>(autonomous)"| Outcome[Approve / Decline / Hold]
    D -->|"Tier 2: irreversible or legal<br/>(recommend only, never auto-executed)"| H
    D -.->|every decision logged| A
    H -.->|escalation outcomes logged| A
    A -->|confirmed/flagged cases| F
    F -->|candidate clusters, human review required| H
    H -->|confirmed clusters only| R
    R -.->|"risk-weight signal<br/>(feeds existing thresholds, never auto-blocks)"| D

    style D fill:#f9a825,color:#000
    style H fill:#c62828,color:#fff
    style S fill:#0288d1,color:#fff
    style I fill:#5bc0de,color:#000
    style A fill:#2e7d32,color:#fff
    style F fill:#8e24aa,color:#fff
    style R fill:#8e24aa,color:#fff
```

**The arrow from Risk Registry → Decision is deliberately drawn as a signal into the existing
threshold system, not a new autonomous path.** The Forensic Attribution Layer can only ever
*recommend*, through the same human-review gate as Tier 2 actions. See
[ADR-006](adr/ADR-006-forensic%20attribution%20feedback.md).

---

## Architecture Decision Records

| ADR | Decision | Status |
|---|---|---|
| [ADR-001](adr/ADR-001-authority-boundary.md) | Model never has autonomous authority over irreversible or legally consequential actions | Accepted |
| [ADR-002](adr/ADR-002-latency-budget.md) | End-to-end latency budget decomposed and enforced per layer | Accepted |
| [ADR-003](adr/ADR-003-failopen-failclosed.md) | Fail-closed by default on scoring timeout, with a narrow pre-approved fail-open exception | Accepted |
| [ADR-004](adr/ADR-004-asymmetric-error-handling.md) | False positives and false negatives handled as distinct, independently-tunable paths | Accepted |
| [ADR-005](adr/ADR-005-audit-explainability.md) | Every decision requires a synchronous, guaranteed-delivery audit record; audit failure is treated as a scoring failure | Accepted |
| [ADR-006](adr/ADR-006-forensic%20attribution%20feedback.md) | Forensic attribution feedback is advisory-only and requires human sign-off before entering the real-time risk registry | Accepted |

Core architecture coverage is now 6 ADRs. ADR-006 extends the system beyond real-time decisioning
into forensic fraud-ring attribution — but deliberately keeps that new capability inside the same
authority model ADR-001 already established, rather than opening a second, unreviewed path to
consequential action.

---

## Simulation: Proving the ADRs Hold

`sim/sentry_sim.py` is a discrete-event proof (not a production model) validating all six ADRs
against 14 scenarios, all passing:

| # | Scenario | ADR |
|---|---|---|
| 1 | Nominal low score → APPROVE | baseline |
| 2 | High score → DECLINE | baseline |
| 3 | Mid-range score → HOLD_FOR_REVIEW (friction band) | ADR-004 |
| 4 | Timeout, high amount/untrusted → HOLD_FOR_REVIEW | ADR-003 (fail-closed default) |
| 5 | Timeout, low amount/trusted/fresh → APPROVE | ADR-003 (bounded fail-open exception) |
| 6 | Timeout, amount just above exception threshold → HOLD_FOR_REVIEW | ADR-003 (boundary enforcement) |
| 7 | Timeout, stale trust cache → HOLD_FOR_REVIEW | ADR-003 (stale ≠ trusted) |
| 8 | Adversarial Tier 2 request → routed to human escalation, never auto-executed | **ADR-001 (core claim)** |
| 9 | Threshold change alters outcome; each record captures its own config | ADR-004 |
| 10 | Audit write failure downgrades an otherwise-APPROVE decision | **ADR-005 (core claim)** |
| 11 | Unconfirmed cluster → zero effect, still APPROVE | ADR-006 |
| 12 | Confirmed registry match → shifts score into friction band via normal thresholds | ADR-006 |
| 13 | Expired registry entry → zero effect, falls back to APPROVE | ADR-006 |
| 14 | Extreme registry weight still caps at DECLINE, never forces Tier 2 | **ADR-006 (core claim)** |

Run it yourself:
```bash
cd module6-fraud-architecture/sim
python sentry_sim.py
```

---

## Repository Structure

```
module6-fraud-architecture/
├── README.md                          ← you are here
├── adr/
│   ├── ADR-001-authority-boundary.md
│   ├── ADR-002-latency-budget.md
│   ├── ADR-003-failopen-failclosed.md
│   ├── ADR-004-asymmetric-error-handling.md
│   ├── ADR-005-audit-explainability.md
│   └── ADR-006-forensic attribution feedback.md
├── diagrams/
│   └── (source diagrams, mirrored from README for standalone viewing)
└── sim/
    └── sentry_sim.py                  ← 14/14 scenarios passing
```

---

## Next Steps

1. Extend the Streamlit dashboard's architecture diagram and Live Simulation tab to include the
   Forensic Attribution Layer and Risk Registry controls, now that the simulation proves them out.