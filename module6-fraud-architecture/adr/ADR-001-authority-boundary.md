# ADR-001: Fraud-Scoring Model Never Has Autonomous Authority Over Irreversible or Legally Consequential Actions

**Status:** Accepted
**Date:** 2026-07-04
**Deciders:** System Architect (portfolio module)

## Context

A real-time fraud-scoring model outputs a risk signal for a transaction or account. The Decision
layer converts that signal into an action. Some actions are cheap to reverse if the model is
wrong (decline a single transaction, ask for step-up verification) — a false positive here costs
a customer friction, and it's correctable within minutes. Other actions are not reversible, or
carry legal weight, if the model is wrong: permanently suspending an account, freezing funds
indefinitely, or referring a customer to law enforcement. A false positive at that tier isn't
friction — it's reputational, legal, and potentially regulatory exposure that cannot be undone by
simply reversing a flag.

If the model (or the automated Decision layer acting on its score) is allowed to execute
irreversible or legally consequential actions autonomously, the system's blast radius on a single
model error, distribution shift, or adversarial input is unbounded. Conversely, routing every
single transaction decision through a human reviewer defeats the purpose of the system — fraud
screening at checkout has a latency budget measured in milliseconds, not the hours a human queue
requires, and no card network or merchant would accept that.

This is the direct financial-domain analogue to Module 5's ADR-001 (the drone's flight-control
boundary): the question is not "can the model be accurate," it's "what is the model trusted to do
alone, and what must always pass through a human," regardless of how confident the model is.

## Decision

Actions are split into two authority tiers, and the model/Decision layer's authority is bounded
by tier, not by confidence score alone:

**Tier 1 — Reversible, real-time actions (model may act autonomously, within calibrated
thresholds):**
- `APPROVE` the transaction
- `DECLINE` the transaction (this transaction only — does not affect account standing)
- `HOLD_FOR_REVIEW` (temporary friction: step-up authentication, delayed settlement)

**Tier 2 — Irreversible or legally consequential actions (model may only recommend; execution
always requires human authorization):**
- Permanent account suspension
- Indefinite fund freeze
- Law-enforcement referral

The Decision layer can output a Tier 2 *recommendation* (e.g., "flag for permanent suspension
review"), but that recommendation is routed to the Human Escalation Layer as a queued item with
an SLA — it is never auto-executed, no matter how high the model's confidence score is.

## Alternatives Considered

| Option | Pros | Cons | Why rejected |
|---|---|---|---|
| Full automation across all actions, including Tier 2 | Fastest, most scalable, no human bottleneck | A single model error, drift event, or adversarial pattern can permanently harm a legitimate customer with no correction path; significant legal/regulatory exposure | Unacceptable blast radius, mirrors the rejected "direct control writes" option in Module 5 ADR-001 |
| Full human review of every decision, including Tier 1 | Maximizes oversight and correctness | Destroys real-time checkout UX; does not scale to transaction volume; card networks and merchants require sub-second decisions | Fails the core latency requirement of the domain |
| Tiered authority split by reversibility (chosen) | Bounds blast radius to reversible actions; matches regulatory expectations of human oversight for high-stakes decisions; preserves real-time UX for the common case | Requires an upfront, careful classification of which actions belong in which tier, and must be revisited as new action types are added | Best tradeoff; same pattern that worked for the drone fail-safe boundary |

## Consequences

**Positive:**
- A model error, drift event, or adversarial transaction pattern can, at worst, cause a declined
  transaction or a temporary hold — never an unrecoverable action against a customer.
- Matches the general regulatory posture (e.g., adverse-action and fair-lending expectations)
  that high-stakes automated decisions affecting a person's access to funds or legal standing
  require a human in the loop.
- Gives the system a legible safety argument, the same way ADR-001 did for the drone system: "the
  model can only ask for the serious actions, never command them."

**Negative / accepted tradeoffs:**
- Requires a resourced Human Escalation Layer with defined SLAs — Tier 2 recommendations that sit
  in a queue too long become their own operational risk (e.g., a fraud ring active while a
  suspension recommendation waits for review).
- The tier classification itself is a standing architectural commitment: any new action type
  added to the system must be explicitly assigned a tier before it can be wired in, or it risks
  defaulting to unsafe autonomous execution.

## Validation

The Module 6 simulation will feed the Decision layer adversarial and malformed model outputs
attempting to force a Tier 2 action (e.g., a spoofed or bugged score payload requesting immediate
permanent suspension) and assert that the action is always routed to the Human Escalation queue,
never executed directly — the same style of proof as the drone module's adversarial-intent test
in `sim/failsafe_sim.py`.