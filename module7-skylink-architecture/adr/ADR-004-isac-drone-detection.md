# ADR-004: ISAC Drone Detection Is Resource-Subordinate to the C2/UTM Slice, and Requires Multi-Static Corroboration Before Affecting Any Connected UAV's State

**Status:** Accepted
**Date:** 2026-07-09
**Deciders:** System Architect (portfolio module)

## Context

ADR-001 through ADR-003 all assume the UAV is a cooperative, connected user equipment — it has a
C2 link, rides the isolated network slice, participates in handovers. Real airspace also contains
**unconnected or uncooperative drones**: not registered, not broadcasting Remote ID, invisible to
everything this module has built so far. The architecture is currently blind to any aircraft that
isn't using it.

Integrated Sensing and Communication (ISAC) closes this gap by using existing cellular
infrastructure as a radar system — transmitting reference signals and analyzing their reflections
to detect, locate, and track objects without requiring them to be connected. The paper reports
strong performance (detection probability targeted at 99% in some scenarios) but also names two
real constraints that this ADR must resolve, not ignore:

1. **Mutual interference between sensing and communication functions.** ISAC shares spectrum and
   hardware with the same radios carrying C2/UTM traffic. Enabling drone detection is not free —
   it is new demand on the exact resources ADR-001 already committed to guaranteeing for connected
   UAVs.
2. **A non-trivial false alarm rate** (the paper cites ~3% in some scenarios). A single ISAC
   detection is meaningfully less certain than a connected UAV's own self-reported telemetry, and
   treating every detection as confirmed fact would either desensitize operators to real threats
   or cause frequent, unwarranted flight disruptions for connected traffic nearby.

This is the same shape of problem this portfolio has resolved twice already — Module 5's ADR-001
(the AI/flight-control boundary) and Module 6's ADR-001 and ADR-006 (the model-authority boundary
and the attribution-feedback boundary): a probabilistic, automated signal must never gain direct
command authority over a consequential action, and a new function must never silently degrade an
already-guaranteed resource.

## Decision

1. **ISAC sensing is resource-subordinate to the C2/UTM slice.** Given the paper's own documented
   mutual-interference constraint, if ISAC sensing activity would degrade the C2/UTM slice's
   latency or bandwidth guarantee from ADR-001, ISAC is throttled or scheduled around that
   guarantee — never the reverse. The slice's SLA, already established as the system's highest
   commitment, is not renegotiated by a newer capability.
2. **A single-node (monostatic) ISAC detection is probabilistic advisory input only.** It can
   feed a situational-awareness display for human operators and UTM systems, but it cannot, by
   itself, change any connected UAV's degradation state or trigger any automated response.
3. **Multi-static corroboration is required before a detection affects connected-UAV state.**
   Only when a detection is corroborated by more than one sensing node (per the paper's described
   multi-static mode) may it elevate a nearby connected UAV into a `DEGRADED` advisory state
   (e.g., cautious hold pattern) via the same bounded intent mechanism already established in
   Module 5's flight-control boundary — never a direct, unmediated command.
4. **ISAC detections never gain autonomous authority over irreversible or high-consequence
   actions** (e.g., autonomous law-enforcement referral, autonomous evasive maneuvering outside
   the whitelisted intent interface). This is the same "propose, never command" pattern already
   applied in Module 5's ADR-001 and Module 6's ADR-001/ADR-006 — now demonstrated a third time,
   across a third distinct type of automated/probabilistic signal.

## Alternatives Considered

| Option | Pros | Cons | Why rejected |
|---|---|---|---|
| ISAC given equal or priority resource allocation alongside C2/UTM traffic | Maximizes detection performance and coverage | Directly risks degrading the guaranteed C2 slice SLA whenever sensing and communication contend for the same spectrum — exactly the mutual-interference problem the paper names | Rejected — violates the slice-isolation priority already established in ADR-001 |
| ISAC detections directly and autonomously command connected-UAV flight-path changes or authority actions | Fastest possible reaction to a detected hazard | Recreates the exact authority-escape problem already closed twice in this portfolio: a ~3%-false-alarm sensor signal would gain direct command authority over consequential actions | Rejected — reopens a boundary this portfolio has consistently closed |
| Single-node detection treated as sufficient confirmation on its own | Fastest response, simplest to implement | At a 3% false alarm rate, treating every detection as actionable causes frequent unnecessary disruption — a "cry wolf" problem that erodes trust in the system over time | Rejected as insufficiently corroborated for a consequential state change |
| ISAC subordinate to C2/UTM resources; multi-static corroboration required; never autonomous authority (chosen) | Preserves the already-established slice guarantee; extends the portfolio's bounded-authority pattern for a third time; explicitly engineers around the documented false-alarm rate instead of ignoring it | Reduces ISAC's effective responsiveness during heavy C2/UTM demand; requires multi-static infrastructure and coordination, adding real complexity | Best tradeoff — consistent with every prior authority-boundary decision in this portfolio |

## Consequences

**Positive:**
- Unconnected and uncooperative drones become visible to the overall airspace picture without
  threatening the guaranteed slice that connected, cooperative operations depend on.
- This is the third instance across the portfolio of the same "propose, don't command" pattern —
  Module 5's AI/flight-control boundary, Module 6's fraud-model/Tier-2 boundary, and now this
  ISAC/connected-UAV-state boundary — which is no longer a one-off design choice but a
  demonstrated, consistent architectural philosophy.

**Negative / accepted tradeoffs:**
- ISAC's effective detection responsiveness is reduced under heavy C2/UTM slice load — an
  accepted tradeoff, prioritizing the already-guaranteed service over the newer sensing
  capability.
- The multi-static corroboration requirement adds real infrastructure and coordination complexity,
  and could delay confirmation in a genuinely urgent single-witness detection. This is disclosed
  explicitly rather than hidden — a faster, less-corroborated response was considered and
  rejected in favor of avoiding false-alarm-driven disruption at scale.

## Validation

The Module 7 simulation will be extended with scenarios asserting:

1. Under simulated concurrent C2 slice demand and ISAC sensing resource contention, the C2 slice's
   SLA (ADR-001) is preserved — ISAC scheduling is throttled, never the guaranteed slice.
2. A single-node ISAC detection alone does not change any connected UAV's degradation state.
3. A multi-static corroborated detection does elevate nearby connected traffic to a `DEGRADED`
   advisory state, and still never autonomously triggers an irreversible or high-consequence
   action on its own.