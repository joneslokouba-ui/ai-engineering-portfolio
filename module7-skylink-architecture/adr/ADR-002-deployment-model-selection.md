# ADR-002: Deployment Model Is Selected by Zone Classification, Not a Single Nationwide Choice — Hybrid With an Explicit Selection Rule

**Status:** Accepted
**Date:** 2026-07-09
**Deciders:** System Architect (portfolio module)

## Context

ADR-001 established that C2/UTM traffic must ride an isolated, SLA-guaranteed network slice. It
did not decide *which* of the paper's three deployment models — FAA Private Network (dedicated
B79 spectrum, 4.5–5 GHz), MNO Network Slice (leveraging the 430,000+ existing U.S. cellular
sites), or a Hybrid of both — actually provides that isolation in a given area, or how to choose
between them.

The three options carry genuinely different tradeoffs, and no single one is correct everywhere:
a private network gives the FAA complete control and the highest assurance, but building it
nationwide duplicates infrastructure that already exists and cannot realistically meet the FAA's
own 2029 modernization timeline at that cost and pace. An MNO slice is fast and cheap to scale
nationwide, but its isolation guarantee ultimately depends on a third party's implementation — an
acceptable trust level for routine, standard-risk airspace, but arguably not for operations near
critical infrastructure (airport final-approach corridors, defense sites, disaster-response
corridors) where the assurance bar is higher.

The paper's own "Hybrid" option (Option 3) names this tradeoff but doesn't resolve it: it states
the hybrid approach "requires coordination between private and public network operations" and
"demands integration to ensure seamless performance," without specifying *which* segments use
which network, or what happens at the boundary between them. Left this vague, "hybrid" isn't an
architecture decision — it's a placeholder for one.

## Decision

Deployment model is selected by **zone classification**, not applied uniformly nationwide:

1. **Standard zones** (the majority of low/medium-altitude airspace — commercial deliveries,
   routine BVLOS, general UAM corridors): **MNO Network Slice** is the default, per ADR-001's
   isolation requirement. This matches the paper's cost/coverage rationale and the FAA's phased
   2027–2029 timeline, which leans on existing MNO infrastructure rather than nationwide private
   buildout.
2. **Critical zones** (airport final-approach corridors, defense/government facilities,
   designated disaster-response corridors): **FAA Private Network** on dedicated spectrum is
   required. The higher assurance and full control this provides is justified by the
   consequence of a failure in these specific areas, not applied as a blanket default.
3. **Transition corridors** (flight paths that cross between standard and critical zones, or
   areas requiring both nationwide roaming and local high-assurance capacity): **Hybrid**, with
   both networks available and an explicit, detectable handover event as the aircraft's C2 link
   transitions from one to the other.
4. **Handover failures are not a special case.** A detected gap or failure during a
   standard-to-critical (or reverse) network transition is reported as a degraded-link condition
   and routed through the *same* Module 5 degradation ladder established in ADR-001 — it does not
   get its own separate failure-handling logic. The zone-classification map itself is a standing,
   periodically-reviewed artifact (airspace usage and critical-infrastructure designations
   change), not a one-time configuration.

## Alternatives Considered

| Option | Pros | Cons | Why rejected |
|---|---|---|---|
| FAA Private Network everywhere | Maximum uniform security and control | Prohibitive capital cost to duplicate 430,000+ existing MNO sites nationwide; unrealistic against the FAA's 2029 timeline | Rejected as the nationwide default — retained only for critical zones where the assurance bar justifies the cost |
| MNO Network Slice everywhere | Fastest, cheapest, leverages existing infrastructure at nationwide scale | Near critical infrastructure, relying solely on a third-party MNO's isolation guarantee (already flagged as a trust dependency in ADR-001) may not meet the assurance bar those zones require | Rejected as the sole approach — retained as the default for standard zones only |
| Hybrid as stated in the paper, without an explicit selection/handover rule | Flexible in principle, matches the paper's own stated direction | "Hybrid" without a defined selection rule and handover-failure policy is underspecified — it names a tradeoff without resolving it | Rejected as insufficiently specified to be an actual architecture decision |
| Hybrid with explicit zone-based selection and handover routed through the existing degradation ladder (chosen) | Captures the paper's recommended flexibility while making selection and failure-handling explicit and testable; matches the FAA's phased, cost-realistic timeline; reuses Module 5's failure semantics instead of inventing new ones | Requires maintaining a zone-classification map as a standing, reviewed artifact; hybrid handover is architecturally more complex than a single-network approach, and depends on reliable handover-event detection | Best tradeoff — resolves the paper's own named ambiguity rather than leaving it open |

## Consequences

**Positive:**
- Avoids both extremes: an unaffordable nationwide private buildout, and under-assured coverage
  near the specific locations where a C2 failure would be most consequential.
- Reuses the already-established Module 5 degradation ladder for handover failures rather than
  inventing parallel failure semantics — keeping the whole portfolio's failure model consistent
  across modules, the same discipline ADR-001 established.

**Negative / accepted tradeoffs:**
- The zone-classification map is itself a standing decision requiring periodic review — airspace
  usage patterns shift, new critical infrastructure gets built, corridors change. This is flagged
  explicitly as ongoing maintenance, not solved once and forgotten.
- Hybrid deployment is architecturally more complex than committing to a single network model.
  The safety guarantee at a transition boundary depends on handover-gap *detection* actually
  working — if that detection itself fails silently, the degradation ladder never triggers. This
  dependency is surfaced here rather than assumed away.

## Validation

The Module 7 simulation will model a flight path crossing from a standard zone (MNO slice) into
a critical zone (FAA Private Network) and assert:

1. The C2 slice's guaranteed-QoS status is continuously maintained through a clean handover.
2. A simulated handover gap (detection failure or timing mismatch between the two networks) is
   correctly reported as a degraded-link condition feeding into Module 5's degradation ladder —
   it never silently continues on unguaranteed connectivity while reporting as nominal.