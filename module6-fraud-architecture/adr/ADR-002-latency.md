# ADR-002: End-to-End Latency Budget Is Decomposed and Enforced Per Layer

**Status:** Accepted
**Date:** 2026-07-04
**Deciders:** System Architect (portfolio module)

## Context

A fraud check at checkout has a hard deadline set by the payment flow, not by the model's
convenience: the transaction has to clear or decline before the customer's card-present or
card-not-present authorization window times out. Illustrative target: card networks and payment
processors typically expect an authorization decision within a few hundred milliseconds; a fraud
score that arrives after the transaction has already settled is operationally useless — the money
has moved.

This is the financial-domain analogue of Module 5's ADR-002 (the drone's reaction-time budget): a
late-but-correct fraud decision is equivalent to a wrong one, because the system it's feeding
(the payment authorization flow) cannot wait for it.

Unlike the drone case, the fraud-scoring pipeline has an additional wrinkle: feature extraction
often depends on external lookups (recent transaction history, device reputation databases,
account velocity checks) that are themselves variable-latency network calls, not local
computation. A budget has to account for this dependency explicitly, not assume it away.

## Decision

The total authorization-window deadline (illustrative target: 300 ms from transaction event to
decision output) is decomposed into a fixed budget per layer, and each layer is required to fail
fast — emit a timeout/degraded signal — rather than emit a late result:

| Layer | Budget | Failure behavior if exceeded |
|---|---|---|
| Ingestion (event receipt + feature extraction, including external lookups) | 150 ms | Emit FEATURE_TIMEOUT flag; do not forward partial/late features as if complete |
| Scoring (model inference) | 100 ms | Emit SCORE_TIMEOUT flag; do not forward a stale or default score silently |
| Decision (thresholding + tiering) | 50 ms | Deterministic, rule-based logic only; must not itself become a latency bottleneck |

A late output at any layer is treated as a failure of that layer and triggers the degraded-mode
handling defined in ADR-003 (fail-open vs. fail-closed policy) — it is never forwarded downstream
as if it had arrived on time.

## Alternatives Considered

| Option | Pros | Cons | Why rejected |
|---|---|---|---|
| Best-effort, single end-to-end timeout only | Simple to configure | Doesn't identify which layer caused a deadline miss (feature lookup vs. model inference vs. thresholding); makes production debugging and vendor/SLA accountability difficult | Insufficient observability, especially since feature lookups often depend on third-party services outside the team's direct control |
| No budget on external feature lookups (assume they're always fast) | Simpler design | External device-reputation or velocity-check services are a common real-world source of variable latency; ignoring this produces an unrealistic architecture | Fails to account for the domain's actual dependency structure |
| Per-layer budget with fail-fast, external lookups explicitly budgeted (chosen) | Deadline misses are attributable to a specific layer; forces explicit degraded-mode behavior instead of silent lateness; matches the proven pattern from Module 5 | Requires timing instrumentation at every layer boundary, including around third-party calls | Best tradeoff; necessary given the domain's dependency on external data sources |

## Consequences

**Positive:**
- Deadline misses are attributable to a specific layer, making it possible to distinguish "our
  model is too slow" from "a third-party device-reputation API is degraded" — an important
  distinction for both engineering response and vendor accountability.
- Forces feature engineering and model selection decisions to be latency-aware from the start,
  the same discipline Module 5's ADR-002 enforced for the drone's perception layer.

**Negative / accepted tradeoffs:**
- Constrains which external data sources can be used for feature extraction — a highly predictive
  but slow third-party lookup may need to be dropped or moved to an asynchronous, post-decision
  enrichment step rather than blocking the real-time path.
- Requires per-layer timestamping instrumentation, adding minor overhead and operational
  complexity (though this pairs naturally with the Audit/Compliance layer's logging requirements).

## Validation

The Module 6 simulation will inject artificial per-layer delays, including simulated third-party
feature-lookup timeouts, and confirm that (a) a layer exceeding its budget emits a timeout signal
rather than a late result, and (b) the Decision layer correctly treats that signal as a trigger
for the fail-open/fail-closed policy in ADR-003, not as valid scoring data.