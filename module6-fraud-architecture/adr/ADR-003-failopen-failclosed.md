# ADR-003: On Scoring-Service Timeout, the System Fails Closed by Default, With a Narrow, Pre-Approved Fail-Open Exception

**Status:** Accepted
**Date:** 2026-07-04
**Deciders:** System Architect (portfolio module)

## Context

When the feature store or scoring service exceeds its latency budget (per ADR-002), the Decision
layer has no valid fraud score to act on and must fall back to a default policy. There are two
naive extremes, and both are dangerous in different directions:

- **Always fail-open (approve automatically on timeout):** preserves revenue and customer
  experience seamlessly, but means that during any outage — including one caused by an active
  attack generating abnormal load — the system approves transactions completely blind. This is
  precisely the condition an attacker benefits most from, and it is the financial-domain
  equivalent of a drone continuing to fly full-speed with no sensor input.
- **Always fail-closed (decline or hold everything on timeout):** never blindly approves
  potential fraud, but an ordinary infrastructure hiccup (a slow third-party device-reputation
  API, a transient network blip) then blocks *all* transactions, including from a business's most
  trusted, long-standing customers. At scale and during peak volume, this is itself a serious
  business and trust cost disproportionate to the actual fraud risk avoided.

Neither extreme reflects how the actual risk is distributed: a $15 purchase from a five-year
account in good standing carries a very different risk profile during a timeout than a $4,000
purchase from a new or previously-flagged account. A single blanket policy ignores this.

## Decision

The default policy on scoring-service or feature-store timeout is **fail-closed to
`HOLD_FOR_REVIEW`** (not autonomous decline, and never autonomous approval) — routing to
temporary friction (step-up verification) or a queued review, consistent with the Tier 1
authority defined in ADR-001.

A single, narrow, **explicitly pre-approved exception** allows fail-open behavior: a transaction
may be auto-approved during a scoring timeout **only if both** of the following hold, checked
against a periodically-refreshed (not live-computed) trust cache:

1. Transaction amount is below a fixed, conservative threshold (illustrative: under $25).
2. The account carries a cached trust tier indicating sustained good standing (illustrative:
   account age > 12 months, no prior fraud flags, refreshed on a scheduled cadence — e.g. daily —
   not computed in the timeout path itself).

Any transaction failing either condition falls back to the default `HOLD_FOR_REVIEW` fail-closed
path. The exception's threshold and trust-tier criteria are a standing business/risk decision,
reviewed on a fixed cadence (illustrative: quarterly), not an engineering default that can silently
drift.

## Alternatives Considered

| Option | Pros | Cons | Why rejected |
|---|---|---|---|
| Always fail-open on timeout | Seamless revenue/UX, no false friction | Approves blind exactly when the system can least verify legitimacy — including during conditions an attacker may have caused | Unbounded fraud exposure during any outage; unacceptable |
| Always fail-closed on timeout | Never approves blind | Blocks all transactions — including trusted, low-risk ones — on any minor infrastructure blip; disproportionate business cost for ordinary transient failures | Too blunt; treats a five-second API hiccup the same as a sustained attack |
| Risk/amount-tiered fail-closed default with narrow pre-approved fail-open exception (chosen) | Bounds worst-case exposure in both directions: a full outage doesn't quietly approve high-risk transactions; a minor blip doesn't block routine purchases from trusted customers | Adds complexity: requires maintaining a periodically-refreshed trust cache and an explicit, reviewed threshold, rather than one simple rule | Best tradeoff; matches how risk is actually distributed across the transaction population |

## Consequences

**Positive:**
- Bounds the worst outcome on both failure directions, rather than optimizing for only one kind
  of error — directly foreshadows the asymmetric false-positive/false-negative reasoning in
  ADR-004.
- The fail-open exception is deliberately small and pre-approved, not a live model decision made
  under degraded conditions — it cannot expand silently as conditions change.

**Negative / accepted tradeoffs:**
- Introduces a second data dependency (the trust-tier cache) that must itself be monitored — if
  the cache goes stale or is unavailable, the system must default to the fail-closed path rather
  than treat a missing cache entry as "trusted by default."
- The threshold and trust-tier criteria are a business risk-acceptance decision, not purely a
  technical one, and require periodic sign-off outside of engineering alone — this is called out
  explicitly rather than left as an implicit configuration value.

## Validation

The Module 6 simulation will simulate scoring-service timeout events across a range of
transaction profiles (amount, trust-tier status, and trust-cache freshness) and assert:

1. A high-amount or unknown-trust-tier transaction during a timeout always resolves to
   `HOLD_FOR_REVIEW`, never autonomous approval.
2. A transaction just below the exception threshold, from a cached-trusted account, resolves to
   `APPROVE`.
3. A transaction just above the exception threshold — otherwise identical — resolves to
   `HOLD_FOR_REVIEW`, proving the threshold boundary is actually enforced and not silently
   rounded or ignored.
4. A stale or missing trust-cache entry is treated as untrusted (fails closed), never as an
   implicit pass.