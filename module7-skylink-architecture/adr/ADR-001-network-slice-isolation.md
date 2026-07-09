# ADR-001: Mission-Critical C2/UTM Traffic Is Isolated via Dedicated Network Slice, Never Sharing a Path With General Public Traffic

**Status:** Accepted
**Date:** 2026-07-09
**Deciders:** System Architect (portfolio module)

## Context

A UAV's Command & Control (C2) link carries the commands that keep it flying safely — real-time
collision avoidance depends on this link maintaining sub-10ms latency, per 5G Standalone's stated
capability. UTM (Unmanned Traffic Management) connectivity carries compliance and coordination
data with similar time sensitivity. Neither is optional traffic; both are safety-relevant in the
same sense that Module 5's flight-control loop is safety-relevant.

If this traffic shares an undifferentiated network path with general public 5G traffic — video
streaming, downloads, ordinary phone use — it competes for the same finite radio resources.
Under load (a packed stadium, a public event, an emergency drawing heavy phone use in the same
cell), general traffic can consume enough bandwidth and scheduling priority to push C2 packet
latency past the threshold at which real-time collision avoidance is no longer meaningfully
"real-time." The danger isn't a dropped video call — it's a UAV whose control link degrades
exactly when local network demand is highest, which is often correlated with the same public
events or emergencies that also increase airspace activity (public safety drones, event
coverage).

This is the network-layer counterpart to Module 5's ADR-001: just as the AI decision layer must
never share a direct, untrusted write path with flight control, C2/UTM traffic must never share
an undifferentiated network path with general public traffic and simply hope for the best under
contention.

## Decision

Mission-critical C2 and UTM traffic is carried on a **dedicated 5G Standalone network slice**,
per the Ericsson paper's network-slicing capability, with:

1. **Guaranteed minimum bandwidth and prioritized scheduling** for the C2/UTM slice, independent
   of general public network load — congestion on the public slice must not degrade the
   guaranteed resources of the C2 slice.
2. **A hard latency SLA** (target: under 10ms one-way, per the paper's stated 5G Standalone
   capability) monitored *per-slice*, not blended into an average across all network traffic —
   an aggregate "network is healthy" metric can hide a specific slice's SLA violation.
3. **Logical isolation as the baseline**, with physical isolation (FAA Private Network or Hybrid
   deployment, per the paper's Table 3) reserved for zones where slice-isolation guarantees alone
   are judged insufficient — this decision doesn't select the deployment model, only that
   isolation must exist.
4. **No silent fallback to best-effort traffic.** If the dedicated slice's SLA cannot be met, the
   UAV's C2 link must report this as a degraded-link condition and feed it into the existing
   degradation ladder established in Module 5's ADR-003 (NOMINAL → DEGRADED → LOST → FAIL_SAFE) —
   never quietly reroute C2 traffic over general best-effort capacity while treating it as
   equivalent to the guaranteed slice.

## Alternatives Considered

| Option | Pros | Cons | Why rejected |
|---|---|---|---|
| Single shared network, no slicing | Simplest, cheapest, fastest to deploy | C2 traffic contends directly with public traffic; the sub-10ms collision-avoidance latency budget cannot be guaranteed under load | Unacceptable — directly threatens flight safety at exactly the times (crowded events, emergencies) when it matters most |
| Dedicated FAA Private Network only | Maximum isolation and security, no contention with public traffic | High capital cost; coverage limited to build-out footprint; doesn't leverage the 430,000+ existing MNO sites the paper cites | Rejected as the *sole* option due to cost and coverage — retained as a targeted option for high-security zones, not the default |
| MNO network slice, no fallback specification | Cost-effective, leverages existing infrastructure, faster to scale | Without an explicit fallback policy, a slice failure could silently degrade to best-effort traffic with no signal to the rest of the system | Rejected as specified — the isolation idea is right, but it must be paired with the explicit degradation-ladder requirement in point 4 above |
| Dedicated slice (MNO or hybrid) with explicit fail-into-degradation-ladder behavior (chosen) | Matches the paper's own stated benefit ("guaranteed bandwidth prevents congestion from public users") while ensuring any failure of that guarantee is visible and handled, not silent | Requires ongoing per-slice SLA monitoring, not just aggregate network health; slice-isolation strength is only as good as the MNO's actual implementation when not using a private network | Best tradeoff — captures the isolation benefit while closing the silent-failure gap other framings leave open |

## Consequences

**Positive:**
- Bounds the effect of public network congestion to a known, reviewed response (the Module 5
  degradation ladder) rather than an invisible latency spike that silently makes collision
  avoidance too slow to matter.
- Keeps this module's failure semantics consistent with Module 5's, rather than inventing a
  parallel and potentially conflicting notion of "degraded" — a link problem here and a sensor
  problem there both resolve through the same reviewed ladder.

**Negative / accepted tradeoffs:**
- Requires active, per-slice SLA monitoring as an ongoing operational commitment, not a one-time
  configuration.
- When using an MNO network slice (Option 2/3 from the paper) rather than a fully private
  network, the isolation guarantee ultimately depends on the MNO's own implementation — a real
  trust dependency that architecture alone cannot fully close, and is flagged here rather than
  hidden.

## Validation

The Module 7 simulation will model network load scenarios — baseline, congested public traffic,
and simulated slice degradation — and assert:

1. Under simulated public-traffic congestion, the modeled C2 slice's latency stays within its
   SLA, while a non-sliced control scenario shows latency exceeding the 10ms threshold under the
   same load.
2. When the C2 slice itself is modeled as degraded or unavailable, the system reports this as a
   degraded-link condition mapping onto Module 5's degradation ladder — it never silently routes
   C2 traffic over general best-effort capacity while treating it as equivalent to the guaranteed
   slice.