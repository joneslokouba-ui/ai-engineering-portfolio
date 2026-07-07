# ADR-001: AI/ML Never Has Direct Write Access to the Flight-Control Loop

**Status:** Accepted
**Date:** 2026-07-03
**Deciders:** System Architect (portfolio module)

## Context

The Decision layer (path planning, obstacle avoidance) runs machine-learned or heuristic models
that can be wrong, slow, or crash. The Control layer runs the hard real-time flight-control loop
(attitude stabilization, motor mixing) that must execute at a fixed rate (e.g. 400 Hz) with
bounded jitter, or the aircraft becomes physically unstable.

If the Decision layer is allowed to write arbitrary commands directly into the control loop, then
any bug, adversarial input, sensor spoofing, model drift, or unhandled exception in the AI stack
becomes a flight-safety incident. This is the single highest-consequence design decision in the
whole system: it determines the blast radius of every future ML bug.

This pattern mirrors a well-established distinction in safety-critical engineering: the
"authority" layer (flight control) is kept small, formally verifiable, and rarely changed, while
the "intelligence" layer (perception, planning) is allowed to be large, frequently updated, and
imperfect — because it is not trusted with direct authority.

## Decision

The Decision layer communicates with the Control layer **only** through a narrow, whitelisted
intent interface (e.g. `HOVER`, `LOITER`, `GOTO(waypoint)`, `RETURN_TO_HOME`, `LAND`). The Control
layer independently validates every intent against hard limits (max velocity, max tilt, geofence)
before execution, and rejects or clamps anything out of bounds. The Control layer has no
dependency on any ML model, library, or non-deterministic code path. It can run, and fail safely,
even if the entire Decision and Perception stack crashes.

## Alternatives Considered

| Option | Pros | Cons | Why rejected |
|---|---|---|---|
| Direct control writes from Decision layer | Lower latency, simpler interface | Any AI bug can directly destabilize the aircraft | Unacceptable blast radius for a safety-critical system |
| Shared process, in-memory calls | Fast, simple to prototype | No fault isolation; a Python exception in the planner can take down the control loop | Fails basic fault-isolation requirement |
| Whitelisted intent interface with independent validation (chosen) | Bounded blast radius; Control layer testable/verifiable in isolation; AI stack can be updated without recertifying flight control | Slightly higher latency per intent; requires careful interface design | Best tradeoff for safety-critical constraint |

## Consequences

**Positive:**
- An ML bug, model drift event, or adversarial perception input can, at worst, cause the drone to
  loiter or return home — never an uncontrolled maneuver.
- The Control layer can be developed, tested, and (in a real system) certified independently of
  the AI stack, and on a much slower release cadence.
- Makes the system's safety argument legible to a non-ML reviewer: "the AI can only ask, never
  command."

**Negative / accepted tradeoffs:**
- Adds a translation/validation step, and therefore latency, between decision and execution
  (quantified in ADR-002).
- Limits the expressiveness of what the Decision layer can request — it cannot micromanage
  low-level control, only select from a pre-approved maneuver set.

## Validation

`sim/failsafe_sim.py` will feed the Control layer a stream of intents that includes malformed,
out-of-bound, and adversarial values (simulating an AI bug or spoofed input) and assert that the
Control layer never executes anything outside its whitelist and safety envelope. This is a
discrete-event proof, not a physics simulation — it demonstrates the boundary holds, not that the
aircraft flies well.