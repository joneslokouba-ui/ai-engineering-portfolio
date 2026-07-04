# ADR-004: False Positives and False Negatives Are Handled as Distinct, Independently-Tunable Architectural Paths

**Status:** Accepted
**Date:** 2026-07-04
**Deciders:** System Architect (portfolio module)

## Context

A fraud-scoring model produces two distinct error types, and they are not interchangeable in
cost or in who bears the consequence:

- **False positive** (legitimate transaction flagged as fraud): the customer is inconvenienced,
  embarrassed at checkout, or in the worst case has funds held or an account frozen. The cost
  lands on a legitimate customer and, cumulatively, on the business's revenue and trust.
- **False negative** (fraudulent transaction approved): the cost lands on the business
  (chargeback liability, card-network penalties) and, if unresolved at scale, on the payment
  ecosystem's trust in the platform.

Treating this as a single "accuracy" or "AUC" optimization target — the common default in ML
tooling — collapses two costs that are not just different in magnitude but different in **who
pays**. A model tuned purely to maximize aggregate accuracy will implicitly pick a single
operating threshold that trades off these two costs in whatever way happens to fall out of the
data, not in a way any stakeholder actually chose. That is an architecture gap, not just a
modeling one: the threshold is a business decision wearing a model's clothing.

This connects directly to ADR-003: the trust-tier and amount threshold defined there was itself
an implicit false-positive/false-negative tradeoff for the timeout case. This ADR makes that kind
of tradeoff an explicit, first-class part of the architecture for the *normal* (non-timeout) path
as well.

## Decision

The Decision layer does not use a single global threshold on the fraud score. Instead, it
exposes **two independently configurable thresholds**, owned by different stakeholders and
reviewable on different cadences:

1. **Decline threshold** — score above this triggers `DECLINE` or `HOLD_FOR_REVIEW`. Tuned
   primarily against false-negative cost (fraud losses, chargeback rate), owned by risk/fraud
   operations.
2. **Approve-with-friction threshold** — score in a middle band triggers step-up verification
   rather than outright decline, giving a legitimate customer a recovery path instead of a flat
   rejection. Tuned primarily against false-positive cost (customer friction, cart abandonment),
   owned jointly by risk operations and product/customer experience.

Both thresholds are configuration, not code, and both are logged with every decision (per the
Audit/Compliance layer) so that a shift in either false-positive or false-negative rate after a
threshold change is directly attributable and reviewable — not discovered months later as an
unexplained trend.

## Alternatives Considered

| Option | Pros | Cons | Why rejected |
|---|---|---|---|
| Single global threshold optimizing aggregate accuracy/AUC | Simple, standard ML default | Implicitly picks a false-positive/false-negative tradeoff no stakeholder explicitly chose; conflates two costs borne by different parties | Hides a business decision inside a model metric |
| Two thresholds, but both owned and tuned solely by the ML team | Faster to iterate, fewer stakeholders in the loop | Risk operations and customer experience teams bear the consequences of the tradeoff but have no direct input into where it's set | Decouples authority from consequence |
| Two independently configurable thresholds, owned by the teams that bear each cost, logged per decision (chosen) | Makes the tradeoff explicit, reviewable, and attributable to a specific configuration change; matches who actually bears each error's cost | Requires cross-team threshold governance instead of a single team's autonomy; more coordination overhead | Best tradeoff; correctness here is inseparable from who is accountable for each error type |

## Consequences

**Positive:**
- A rise in customer complaints about wrongful declines and a rise in chargeback losses can now
  be traced to two independently reviewable configuration values, rather than one opaque model
  threshold.
- Gives non-ML stakeholders (risk operations, customer experience) a legitimate, direct lever
  over the cost they are accountable for, instead of relegating them to filing feedback about
  model behavior after the fact.

**Negative / accepted tradeoffs:**
- Requires threshold-change governance (who can adjust which threshold, and a review/approval
  step) rather than a single team pushing a model update independently — this is a deliberate
  slowdown in exchange for accountability.
- Two thresholds interacting (decline vs. friction band) require joint testing when either
  changes, since moving one can shift the effective population hitting the other.

## Validation

The Module 6 simulation will run a fixed distribution of transaction scores through the Decision
layer under multiple threshold configurations and assert:

1. Moving the decline threshold changes the false-negative-eligible population without silently
   also shifting the friction-band population in an untracked way.
2. Every decision emitted carries the threshold configuration that produced it, so a downstream
   audit query can reconstruct exactly which policy was active for any historical transaction —
   directly exercising the Audit/Compliance layer's requirement.