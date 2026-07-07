# ADR-002: End-to-End Latency Budget Is Decomposed and Enforced Per Layer

**Status:** Accepted
**Date:** 2026-07-03
**Deciders:** System Architect (portfolio module)

## Context

A drone reacting to an obstacle has a hard deadline set by physics: closing speed, sensor range,
and required stopping/avoidance distance. If the combined perception → decision → control →
actuation pipeline exceeds that deadline, the "correct" output arrives too late to matter — a
late-but-correct decision is operationally equivalent to a wrong one.

Unlike typical ML systems, this is not "make it fast" as a nice-to-have; it is a hard constraint
each layer must individually meet, because a slow layer cannot be compensated for by a fast one
downstream.

## Decision

The total reaction deadline (illustrative target: 150 ms from sensor capture to actuator command,
for a drone closing on an obstacle at moderate speed) is decomposed into a fixed budget per layer,
and each layer is required to fail fast (emit a STALE/timeout signal) rather than emit a late
result, if it cannot meet its budget:

| Layer | Budget | Failure behavior if exceeded |
|---|---|---|
| Perception (sensor fusion + edge inference) | 50 ms | Emit STALE flag, do not emit a late frame |
| Decision (planning + obstacle avoidance) | 60 ms | Emit DEGRADE_MODE intent, do not emit a late plan |
| Control validation + actuation | 40 ms | Hard real-time loop; cannot be exceeded by design (deterministic code only) |

A late output at any layer is treated as a failure of that layer, not forwarded downstream as if
it were on-time.

## Alternatives Considered

| Option | Pros | Cons | Why rejected |
|---|---|---|---|
| Best-effort, no per-layer budget | Simpler to implement | No way to reason about whether the system meets its physical deadline; failures surface late and are hard to diagnose | Fails the core safety requirement |
| Single end-to-end timeout only | Easier to configure | Doesn't identify which layer is responsible when the deadline is missed; can't optimize the right component | Insufficient observability for a safety-critical system |
| Per-layer budget with fail-fast (chosen) | Deadline misses are localized and diagnosable; forces explicit degrade behavior instead of silent lateness | Requires more careful timing instrumentation per layer | Best tradeoff; matches the "explicit degradation" philosophy in ADR-003 |

## Consequences

**Positive:**
- Deadline misses are attributable to a specific layer, which makes debugging and post-flight
  log analysis tractable (ties into the observability work from Module 3's MLOps pipeline).
- Forces model and code choices at each layer to be latency-aware from the start, rather than
  discovered as a problem after integration.

**Negative / accepted tradeoffs:**
- Constrains model selection at the Perception layer — a more accurate but slower model may be
  rejected in favor of a faster, slightly less accurate one, if it cannot meet its 50 ms budget.
- Requires instrumentation (timestamping at every layer boundary) that adds minor overhead.

## Validation

`sim/failsafe_sim.py` will inject artificial per-layer delays and confirm that (a) a layer
exceeding its budget emits a STALE/DEGRADE signal rather than a late result, and (b) the
downstream layer correctly treats that signal as a trigger for degraded-mode behavior (see
ADR-003), not as valid data.