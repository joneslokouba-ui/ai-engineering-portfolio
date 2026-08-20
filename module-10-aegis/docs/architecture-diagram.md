flowchart TD
    A[Transaction Stream<br/>Simulated Ledger] --> B[Ingestion Layer]
    B --> C[Feature Engineering]
    C --> C1[Wallet Clustering<br/>Common-Input Heuristic]
    C --> C2[Velocity Analysis]
    C --> C3[Graph Centrality<br/>Betweenness / Degree]
    C --> C4[Mixer/Tumbler<br/>Proximity Score]
    C1 --> D[Ensemble Risk Scoring]
    C2 --> D
    C3 --> D
    C4 --> D
    D --> D1[Gradient-Boosted<br/>Classifier]
    D --> D2[Sanctions/Watchlist<br/>Rule Match]
    D1 --> E[Composite Risk Score]
    D2 --> E
    E --> F{Risk Threshold<br/>Exceeded?}
    F -->|No| G[Archive — Low Risk]
    F -->|Yes| H[Escalation Queue]
    H --> I[Human Adjudication]
    I -->|Cleared| G
    I -->|Confirmed| J[Case File + Evidence Trail<br/>Human-Filed SAR]

    style I fill:#f9d67a,stroke:#333,stroke-width:2px
    style J fill:#f4a6a6,stroke:#333,stroke-width:2px