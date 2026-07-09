# ADR-003: Aerial UEs Use a Dedicated Cell Layer With Bounded Handover Latency, Not Default Ground-Optimized Mobility Logic

**Status:** Accepted
**Date:** 2026-07-09
**Deciders:** System Architect (portfolio module)

## Context

ADR-001 established a sub-10ms latency budget for the C2/UTM slice. That budget assumes a stable
serving cell — but the Ericsson paper documents a specific, well-characterized problem for aerial
user equipment (UEs) that threatens exactly that assumption. Ground-optimized 5G networks
downtilt base station antennas to concentrate coverage on the ground and minimize inter-cell
interference; aerial UEs, such as UAVs, are consequently often served by antenna *sidelobes*
(lower gain than the main lobe), and the stronger line-of-sight propagation typical at altitude
can still deliver a usable signal from several cells simultaneously. At medium altitude, this
means an aerial UE can "see" multiple cells at similar strength via main or sidelobes at once —
which causes elevated intra-frequency interference and, critically, frequent handovers as the UE
oscillates between candidate serving cells during ordinary horizontal flight.

Each handover event introduces a brief interruption and re-negotiation. A ground-optimized
mobility policy, tuned for pedestrians and vehicles that see one dominant cell at a time, will
trigger handovers far more often for a fast-moving, high-altitude UE that can see many cells —
and if those interruptions stack up during a flight, the C2 slice's *actual delivered* latency
can exceed the ADR-001 budget even though the network's baseline capability is sub-10ms under
ideal, non-mobile conditions. The paper names this problem directly (Figure 3: "Interference at
different heights") but frames it as a network-optimization challenge rather than a safety-budget
question. This ADR treats it as the latter.

## Decision

Aerial UEs are served through a **dedicated aerial cell layer**, configured on top of existing
ground infrastructure rather than requiring new towers, with:

1. **Aerial cell configuration.** Selected existing ground cells are designated as aerial cells
   with adapted SSB (Synchronization Signal/PBCH Block) radiation patterns, forming a distinct,
   wider aerial coverage layer. Each sector supports two NR cells — one ground, one aerial — so
   this is a configuration decision on existing infrastructure, not a capital buildout, keeping
   it consistent with ADR-002's cost/coverage philosophy.
2. **Distinct SSB frequencies for the aerial layer**, separate from the ground layer and from
   neighboring aerial cells, specifically to control the intra-frequency interference the paper
   documents — this directly addresses the mechanism, not just its symptom.
3. **Mobility policy biased toward the aerial layer.** Inter-frequency mobility configuration in
   both IDLE and CONNECTED modes keeps aerial UEs preferentially served within the aerial cell
   layer during horizontal flight and vertical takeoff/landing, rather than triggering handovers
   based on default ground-cell signal thresholds.
4. **A bounded, quantified handover-latency sub-budget**, explicitly carved out of ADR-001's
   overall sub-10ms SLA. If a specific handover event's projected interruption would push
   effective C2 latency past that sub-budget, the event is treated as a candidate degraded-link
   condition and reported into Module 5's degradation ladder — it is not silently absorbed as
   ordinary network behavior.

## Alternatives Considered

| Option | Pros | Cons | Why rejected |
|---|---|---|---|
| Default ground-optimized handover/mobility logic, unmodified for aerial UEs | No extra engineering; reuses existing network configuration as-is | The paper's own findings show aerial UEs face elevated interference and frequent handovers from multi-cell visibility via sidelobes — this directly threatens the sub-10ms SLA ADR-001 already committed to | Rejected — incompatible with a safety-relevant latency budget already in place |
| Dedicated new aerial-only towers, separate from ground network | Eliminates sidelobe/interference issues with purpose-built aerial coverage | Massive capital cost; duplicates the very ground infrastructure ADR-001 and ADR-002 are architected to leverage cost-effectively; contradicts ADR-002's zone-based, cost-realistic deployment philosophy outright | Rejected as disproportionate to the problem |
| Aerial-optimized cell configuration on existing infrastructure, with a quantified handover-latency sub-budget feeding the degradation ladder (chosen) | Reuses existing infrastructure consistent with ADR-002; directly addresses the paper's documented interference mechanism; bounds and monitors handover risk instead of assuming the baseline latency claim holds unconditionally | Requires real SSB planning and dual-layer cell configuration expertise from the network operator; handover-budget breach detection is a dependency the architecture cannot fully guarantee without operational verification | Best tradeoff — closes a specific, named gap in the source material rather than assuming it away |

## Consequences

**Positive:**
- Directly closes a gap the source paper documents but doesn't resolve as a safety-budget
  question — the sub-10ms SLA now accounts for handover behavior, not just steady-state
  conditions.
- Extends Module 5's degradation ladder to a *third* distinct failure mechanism (after
  slice-unavailability in ADR-001 and zone-transition gaps in ADR-002), reinforcing that the
  ladder is a genuinely reusable architectural contract across this module, not a one-off
  mechanism borrowed once and forgotten.

**Negative / accepted tradeoffs:**
- Requires real network-engineering effort (SSB frequency planning, dual-layer cell
  configuration) from whichever operator — MNO or FAA private network — implements this; it is
  not a default that any 5G Standalone deployment provides out of the box.
- The handover-latency-budget breach detection itself is a dependency this architecture surfaces
  but cannot fully guarantee without operational verification, the same category of dependency
  already flagged in ADR-002's handover-gap detection.

## Validation

The Module 7 simulation will model a UAV in horizontal flight at medium altitude crossing
overlapping ground-cell coverage, with and without aerial-cell configuration, and assert:

1. Without aerial-cell configuration, simulated handover frequency and cumulative
   handover-induced latency exceed the sub-budget carved out of ADR-001's overall SLA.
2. With aerial-cell configuration (mobility bias toward the aerial layer, distinct SSB
   frequencies), handover frequency and cumulative latency stay within budget under the same
   flight path.
3. A simulated handover event that would breach the budget is reported into Module 5's
   degradation ladder rather than executed silently as ordinary network behavior.