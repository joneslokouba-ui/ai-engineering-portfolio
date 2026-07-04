# ADR-005: Every Decision Requires a Synchronous, Guaranteed-Delivery Audit Record — Audit-Write Failure Is Treated as a Scoring Failure

**Status:** Accepted
**Date:** 2026-07-04
**Deciders:** System Architect (portfolio module)

## Context

ADR-001 through ADR-004 establish a system that makes automated, consequential decisions about
real money and, in the Tier 2 case, real legal standing — and that tunes those decisions against
configurable thresholds owned by different stakeholders. None of that is verifiable after the
fact unless every decision can be reconstructed: what feature values were used, what score the
model produced, which threshold configuration was active, and what action resulted. Without this,
a customer dispute, a chargeback defense, or a regulatory inquiry into why a specific transaction
was declined has no authoritative answer — and a claim like "we changed the decline threshold and
false negatives dropped" (ADR-004) is unfalsifiable without a record tying outcomes to the
configuration active at the time.

The harder question is what happens when the audit-logging subsystem itself is degraded or
unavailable. If decisions are allowed to proceed *without* a confirmed audit record whenever the
logging sink is slow or down, then the audit trail has its biggest gap during exactly the
conditions most likely to warrant later scrutiny — an incident, an attack, or a threshold
misconfiguration. An audit system that only works when nothing is going wrong is not actually
serving its purpose.

## Decision

1. Every decision emitted by the Decision layer — a Tier 1 automated outcome, a Tier 2
   recommendation, or a resolved human escalation — must be paired with a **synchronous,
   guaranteed-delivery** audit record before the decision is considered final. The record
   includes: transaction identifier, a versioned feature snapshot (or reference to one), the
   fraud score, the model version, the active threshold configuration (per ADR-004), the
   resulting action, and per-layer timing (per ADR-002).
2. If the audit write cannot be confirmed within a short, tight budget — tighter than the overall
   decision latency budget — the Decision layer treats this exactly as it would treat a scoring
   timeout: it falls back to the fail-closed policy defined in ADR-003. **A decision that cannot
   be logged does not get to bypass the log.**
3. Audit records are immutable (append-only) and independently queryable by transaction ID,
   account ID, or time range, without requiring reconstruction from the live decision path.

## Alternatives Considered

| Option | Pros | Cons | Why rejected |
|---|---|---|---|
| No formal audit requirement; rely on incidental application/model logs | No added engineering effort | Unstructured, typically mutable, not designed for dispute reconstruction or regulatory query; insufficient the moment any single decision is formally challenged | Fails the basic purpose of an auditable system |
| Asynchronous, best-effort ("fire and forget") audit logging | Doesn't couple decision latency or availability to the audit sink's health | The audit sink is most likely to be unhealthy during exactly the conditions — incidents, attacks, misconfigurations — where the record is needed most; creates the largest gap at the worst time | Undermines the entire purpose of having an audit requirement |
| Synchronous, guaranteed-delivery audit write, fail-closed on audit failure (chosen) | Audit completeness is never "best effort"; matches how seriously ADR-001 treats the downstream consequences of decisions | Couples audit-sink health directly to decision throughput — an audit outage becomes a decision-availability incident | Accepted as the correct prioritization: an unrecorded consequential decision is worse than a delayed one |

## Consequences

**Positive:**
- Any Tier 1 or Tier 2 outcome can always be reconstructed after the fact — there is no scenario
  in which "we don't actually know why the system decided this" is possible, which is essential
  for dispute resolution, chargeback defense, and regulatory examination.
- Makes ADR-004's threshold-attribution claim actually verifiable, closing the loop between that
  decision and this one.

**Negative / accepted tradeoffs:**
- The audit sink becomes a hard dependency for the entire decision path: its reliability directly
  gates transaction throughput. This is a deliberate, disclosed tradeoff, not an oversight — but
  it means the audit sink itself now needs its own high-availability design, which is flagged
  here as a follow-up concern rather than solved by this ADR.
- Some transient audit-sink hiccups that could have been safely buffered and retried will instead
  trigger the fail-closed path unnecessarily; this is accepted in exchange for never silently
  dropping a record.

## Validation

The Module 6 simulation will simulate an audit-write timeout occurring during an otherwise
nominal, healthy transaction and assert that the Decision layer falls back to the ADR-003
fail-closed path rather than returning a finalized decision with no corresponding audit record —
proving that audit completeness is enforced structurally, not left to best effort.