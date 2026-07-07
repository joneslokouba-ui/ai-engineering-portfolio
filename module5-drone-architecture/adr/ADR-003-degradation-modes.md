# ADR-003: Explicit Degradation Ladder for Sensor, Model, and Comms Failure

**Status:** Accepted
**Date:** 2026-07-03
**Deciders:** System Architect (portfolio module)

## Context

Failures are not binary (working / crashed) in a real deployment — a camera can degrade
gradually, a model's confidence can drop without an outright error, and a comms link can become
intermittent before it fully drops. A system that only handles "fully working" and "fully failed"
will make poor decisions in the much more common middle ground.

Without an explicit, named ladder of degradation states, failure handling tends to be implemented
ad hoc, inconsistently, per-engineer, per-incident — which is exactly how safety-critical systems
accumulate unreviewed edge-case behavior.

## Decision

Define a small, fixed set of degradation states that every layer reports into, and that the
Decision layer uses to select a whitelisted intent (per ADR-001). Layers cannot invent new states;
they must map their internal condition onto this fixed ladder:

1. **NOMINAL** — all inputs fresh, confidence above threshold.
2. **DEGRADED** — input stale or confidence below threshold, but within recent history; system
   attempts limited-authority operation (e.g. reduced speed, tighter geofence).
3. **LOST** — required input has been missing/invalid beyond a bounded retry window; system
   commits to a pre-defined safe maneuver (loiter or return-to-home), not further improvisation.
4. **FAIL-SAFE** — comms and primary sensing both unavailable; system executes the single most
   conservative pre-programmed action (e.g. controlled land at current position) with no further
   decision-making.

Each layer reports its own state; the Decision layer takes the **worst** state across all inputs
it depends on, not an average or majority vote.

## Alternatives Considered

| Option | Pros | Cons | Why rejected |
|---|---|---|---|
| Ad hoc, per-failure-type handling | Fast to write initially | Inconsistent, hard to review, easy to miss a case | Unacceptable for safety review |
| Binary healthy/failed only | Very simple | Cannot express partial degradation, which is the common case | Loses too much information to act well |
| Fixed four-state ladder, worst-of aggregation (chosen) | Reviewable, testable, consistent across layers; matches common practice in safety-critical systems (e.g. aviation degraded-mode design) | Requires discipline to map every failure onto the fixed ladder rather than special-casing | Best tradeoff; keeps the decision space small enough to fully test |

## Consequences

**Positive:**
- Every failure mode in the system, however novel, must be classified into one of four known
  states — this bounds the testing surface to a tractable set of scenarios.
- "Worst-of" aggregation means a single degraded sensor cannot be masked by other healthy inputs,
  which prevents a class of dangerous silent-failure bugs.

**Negative / accepted tradeoffs:**
- Coarser than a fully custom response per failure type — some scenarios will be handled more
  conservatively than a bespoke solution might allow.
- Requires every new sensor or model added to the system to explicitly define its mapping onto
  the four states before integration.

## Validation

`sim/failsafe_sim.py` will simulate independent failures (sensor stale, low model confidence,
comms drop) both individually and in combination, and assert that the Decision layer always
reports the worst applicable state and selects the correspondingly conservative whitelisted
intent — never a more permissive one.