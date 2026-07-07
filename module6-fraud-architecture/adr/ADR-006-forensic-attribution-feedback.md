# ADR-006: Forensic Attribution Feedback Is Advisory-Only and Requires Human Sign-Off Before Entering the Real-Time Risk Registry

**Status:** Accepted
**Date:** 2026-07-06
**Deciders:** System Architect (portfolio module)

## Context

The real-time path (Ingestion → Scoring → Decision, ADR-001 through ADR-004) evaluates each
transaction independently. It has no visibility into cross-transaction or cross-account patterns
that only become visible once confirmed fraud cases accumulate and are analyzed together — for
example, the same device fingerprint used to open forty "new" accounts over a month, indicating a
coordinated fraud ring rather than forty unrelated bad actors. A **Forensic Attribution Layer**,
run asynchronously against the Audit/Compliance log (ADR-005), can surface these origin clusters
after the fact. Feeding that intelligence back into the real-time Decision layer closes a real
blind spot: without it, every transaction is scored in isolation, forever blind to network context
that the system itself already has evidence of.

The risk is in *how* that feedback happens. Attribution clustering is inherently noisier than
per-transaction scoring: shared infrastructure (a corporate NAT, public wifi, a household's
devices) routinely produces identifier overlaps between people who have never met. If a discovered
cluster is allowed to automatically and immediately block every account or device sharing that
identifier, the Forensic Attribution Layer becomes a second, unreviewed path to exactly the kind
of population-scale, autonomous consequential action that ADR-001 was written to prevent for
individual transactions. A clustering bug or a legitimately shared IP could cause mass wrongful
declines or suspensions with no human ever in the loop — a larger blast radius than any single
mis-scored transaction, arrived at through a side door.

## Decision

1. The Forensic Attribution Layer runs **asynchronously**, outside the real-time path — it is not
   subject to the ADR-002 latency budgets, since it operates on historical, confirmed/flagged
   cases rather than in-flight transactions.
2. Candidate origin clusters it produces (shared device fingerprint, IP range, payment instrument,
   or account-creation pattern across confirmed fraud cases) are **recommendations only**. No
   identifier enters the real-time Decision layer's Risk Registry without a human fraud-operations
   reviewer explicitly confirming the cluster — the same human-authorization requirement ADR-001
   places on individual Tier 2 actions, extended here to population-level additions.
3. Once confirmed, a registry entry acts as an **additive risk-weight signal**, not a verdict: a
   transaction matching a confirmed entry has that weight factored into its fraud score *before*
   ADR-004's existing thresholds are applied — pushing it toward `HOLD_FOR_REVIEW` or `DECLINE`
   through the same governed threshold mechanism already in place. It never triggers a separate,
   independent auto-block path. Tier 2 actions (permanent suspension, fund freeze, law-enforcement
   referral) still require the full ADR-001 human-escalation process, even for confirmed registry
   members — attribution can never itself authorize an irreversible action.
4. Registry entries **expire on a fixed review cadence** (illustrative: 90 days) and require active
   re-confirmation to persist, preventing an identifier from remaining flagged indefinitely after
   the underlying link has gone stale (e.g., a shared IP later reassigned to an unrelated user).

## Alternatives Considered

| Option | Pros | Cons | Why rejected |
|---|---|---|---|
| Fully automated feedback: clusters immediately gate future transactions with no human step | Fastest reaction time, closes a ring's exploitation window quickly | Clustering false positives (shared legitimate infrastructure) can cause mass wrongful declines with zero human check; recreates the exact autonomous-authority problem ADR-001 was written to prevent, via a population-level route instead of a per-transaction one | Rejected — the reaction-speed gain doesn't justify reopening the authority boundary through a side door |
| No feedback loop at all — attribution stays purely retrospective reporting for investigators | Simplest; zero automation cascade risk | The real-time system never benefits from cross-case fraud-ring intelligence it already has evidence for; the same ring can keep re-attacking with new accounts indefinitely | Rejected — gives up the core value of building attribution in the first place |
| Human-confirmed feedback as an additive risk-weight into existing thresholds, with expiry (chosen) | Captures the cross-case intelligence value while keeping every consequential action inside the already-governed authority tiers (ADR-001) and threshold system (ADR-004); bounds a bad cluster's damage to "more likely to be held for review," not mass autonomous decline/suspension; time-boxes stale links | Slower to react than full automation; requires ongoing fraud-ops reviewer bandwidth to confirm and periodically re-confirm clusters | Best tradeoff — preserves a single, consistent authority model across the entire architecture |

## Consequences

**Positive:**
- Closes the real-time system's cross-transaction blind spot without introducing a second,
  unreviewed path to consequential action — every effect of attribution feedback still resolves
  through either the governed threshold system (ADR-004) or explicit human sign-off (ADR-001).
- Bounds the worst case of a bad or stale cluster to additional friction (a hold, not an
  irreversible action), consistent with the reversible/irreversible split ADR-001 already
  established.

**Negative / accepted tradeoffs:**
- Introduces a reviewer workload and an implicit SLA for cluster confirmation; an unreviewed
  backlog of candidate clusters is itself an operational risk, the same category of risk already
  flagged for the Tier 2 escalation queue in ADR-001.
- Registry entries require active lifecycle management (expiry, re-confirmation) — without it,
  they silently become stale and inaccurate rather than simply absent, which is a real ongoing
  maintenance cost, not a one-time setup task.

## Validation

The Module 6 simulation will be extended with scenarios asserting:

1. An **unconfirmed** candidate cluster has zero effect on any real-time decision — attribution
   output that hasn't been human-approved must not influence scoring at all.
2. A **confirmed, non-expired** registry match shifts the effective decision toward
   `HOLD_FOR_REVIEW` or `DECLINE` through the normal threshold path — never through a separate
   auto-block mechanism.
3. A **confirmed but expired** registry entry no longer affects the decision, falling back to
   ordinary per-transaction scoring.
4. An adversarial attempt to have a registry match directly trigger a Tier 2 action for all
   cluster members is rejected and routed to human escalation — proving the ADR-001 boundary
   holds even against a population-level, attribution-driven attempt to bypass it.