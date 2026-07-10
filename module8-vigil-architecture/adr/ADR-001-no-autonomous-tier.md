# ADR-001: The System Never Outputs a Diagnosis or Treatment Recommendation — Only Ranked Differential Possibilities With Explicit Uncertainty, for Clinician Review

**Status:** Accepted
**Date:** 2026-07-09
**Deciders:** System Architect (portfolio module)

## Context

Modules 5, 6, and 7 each drew a boundary between what an automated or probabilistic system could
decide alone and what required human authorization. In every prior case, *some* tier of action was
judged safe to automate: Module 5's drone could autonomously loiter or return home; Module 6's
fraud model could autonomously approve or decline a single transaction; Module 7's connectivity
layer could autonomously select a network slice. In each case, the automated tier was bounded to
actions with recoverable, contained cost.

This module has no such tier. The system combines population-level antimicrobial resistance
context (regional resistance rates for specific pathogen-drug combinations, per WHO's GLASS
reporting) with a clinician-entered symptom presentation to surface possible conditions. But a
differential-diagnosis or treatment suggestion is not like a declined transaction — a wrong
autonomous nudge here does not cost money that can be refunded or a flight that can be re-flown.
It can cost a person's correct and timely treatment. Given that GLASS itself reports that
resistance patterns vary substantially by region and are still incompletely characterized in
large parts of the world (regional gaps persist despite participation quadrupling since 2016),
any system in this domain is working with real, quantified uncertainty at the population level
before a single patient is even considered.

The temptation in system design is to ask "how do we bound the automated tier safely," following
the pattern of Modules 5–7. The correct question here is different: **whether an automated tier
should exist at all.** This ADR answers that question directly, rather than defaulting to the
prior pattern out of habit.

## Decision

The system has **no autonomous action tier**. At every layer — surveillance trend detection,
diagnostic context ranking, and any downstream consumer — the only permitted output is a **ranked
list of differential possibilities, each carrying an explicit confidence/uncertainty measure**,
directed at a clinician for review. Specifically:

1. The system never outputs a single "most likely" answer framed as a conclusion — only a ranked
   set with visible uncertainty, so no output can be mistaken for a decision already made.
2. The system never outputs a treatment or dosing recommendation of any kind — that determination
   belongs entirely to a licensed clinician, informed by direct patient assessment this system
   does not and cannot perform.
3. No component of the system — including any future extension — may be granted a Tier 1
   "autonomous but reversible" action analogous to Modules 5–7's bounded automated tiers. If a
   future capability seems to warrant one, that is a new architectural decision requiring its own
   ADR and explicit justification for why this domain's default of zero autonomy should be
   relaxed — it is not something a lower-level implementation choice can introduce silently.
4. Every output is traceable to the exact data vintage (which GLASS reporting cycle) and model
   version that produced it, so a clinician can weigh not just the suggestion but its currency and
   provenance.

## Alternatives Considered

| Option | Pros | Cons | Why rejected |
|---|---|---|---|
| Bounded autonomous tier for "low-stakes" outputs (e.g., auto-surfacing common, low-severity conditions without clinician review) | Faster, matches the pattern used successfully in Modules 5–7 | There is no reliably "low-stakes" output in a diagnostic context — a condition that looks common and mild can share early symptoms with something severe; the whole point of differential diagnosis is resolving exactly that ambiguity, which this system cannot do alone | Rejected — importing the Modules 5–7 pattern here assumes a safe-to-automate tier exists, which this domain does not support |
| Single best-guess output with a confidence score, framed as a recommendation | Simpler UI, faster clinician read | Framing anything as "the recommendation" invites anchoring bias even with a stated confidence score attached — time-pressured clinical decision-making is exactly the condition under which a confidently-framed single answer gets over-trusted | Rejected — the framing itself is the risk, independent of the underlying model's actual accuracy |
| No autonomous tier anywhere; ranked possibilities with explicit uncertainty only (chosen) | Removes the possibility of an autonomous wrong action entirely; keeps the system honestly positioned as decision support, not a decision-maker; matches how real WHO GLASS data is presented — aggregate, uncertain, regionally uneven — rather than overclaiming certainty the underlying data doesn't have | Slower to act on than an automated recommendation; still depends on the clinician correctly interpreting ranked uncertainty rather than defaulting to the top-ranked item anyway | Best and only defensible choice for this domain — the tradeoffs of the rejected options are not recoverable the way a declined transaction or a rerouted drone is |

## Consequences

**Positive:**
- Bounds the system's worst-case failure to "the clinician received an unhelpful or incomplete
  list," never "the system acted wrongly on a patient" — the two failure modes are not
  comparable in severity, and this ADR ensures only the recoverable one is possible.
- Extends the portfolio's "propose, never command" pattern to its logical limit: a domain that
  gets *zero* autonomous tier, not just a bounded one — demonstrating that the underlying
  principle is domain-cost-aware, not a template applied uniformly regardless of stakes.

**Negative / accepted tradeoffs:**
- The system is necessarily slower to translate into action than an automated recommendation
  would be — this is accepted as correct given the irreversibility of the harm a wrong autonomous
  suggestion could cause.
- The system's value depends entirely on clinicians engaging with ranked uncertainty rather than
  reflexively treating the top-ranked possibility as a de facto diagnosis — a UI/communication
  problem this ADR flags but does not solve; that is scoped to ADR-003 (uncertainty communication
  format).

## Validation

The Module 8 simulation will assert, by construction rather than by testing a threshold:

1. No function anywhere in the codebase has a return type or code path capable of producing a
   single unranked "diagnosis" or "recommended treatment" output — output types are structurally
   limited to ranked-list-with-uncertainty, the same way Module 7's `isac_detection_effect()` had
   no code path beyond `DEGRADED`.
2. Injecting an adversarial or malformed input that attempts to force a single high-confidence
   "answer" output is rejected or reshaped back into a ranked, uncertainty-qualified list — proof
   that the no-autonomous-tier boundary holds even under an attempt to collapse it, the same style
   of adversarial proof used in Modules 5–7.