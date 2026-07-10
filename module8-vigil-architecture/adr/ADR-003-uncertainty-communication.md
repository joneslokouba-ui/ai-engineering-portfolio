# ADR-003: Ranked Possibilities Are Displayed as Qualitative Confidence Bands With Per-Item Evidence and Persistent Non-Diagnostic Framing — Never a Bare Ranked List or a Numeric Point Estimate

**Status:** Accepted
**Date:** 2026-07-09
**Deciders:** System Architect (portfolio module)

## Context

ADR-001 established that the system only ever outputs ranked possibilities with uncertainty —
never a diagnosis. That decision is only as strong as its presentation. Clinical decision-support
literature on automation bias and alert fatigue shows that a single top-ranked item, especially
with a precise-looking numeric confidence score attached, gets anchored on and over-trusted by
time-pressured clinicians — regardless of how honestly the underlying system intended the number.
A disclaimer shown once at onboarding is reliably ignored once real time pressure sets in. And
ADR-002's UNKNOWN/STALE data states are only useful if they are visible at the point of decision,
not buried in a separate data-quality report the clinician never opens.

## Decision

1. **No single top-ranked item is ever displayed alone.** Every output shows at least 2-3 ranked
   possibilities together, so no UI pattern resembles an "answer box."
2. **Confidence is expressed as qualitative bands** (e.g., "supported by strong regional
   evidence," "weak/uncertain signal"), tied directly to the underlying data's recency and
   coverage confidence from ADR-002 — never a bare numeric percentage, which implies a precision
   the data does not have.
3. **Every ranked item carries its supporting and conflicting evidence inline** (which reported
   symptoms match, which don't, what regional resistance context contributed) — the clinician
   sees the reasoning, not just a label.
4. **A persistent, non-diagnostic framing header** ("Differential considerations for clinical
   review — not a diagnosis") appears on every output screen, not once at onboarding.
5. **UNKNOWN/STALE data flags from ADR-002 are carried through and shown per-item**, never
   simplified away into a falsely clean list.

## Alternatives Considered

| Option | Pros | Cons | Why rejected |
|---|---|---|---|
| Single top-ranked suggestion with a numeric confidence percentage | Simplest, fastest to scan | Implies false precision given ADR-002's data gaps; single-item framing invites exactly the anchoring/automation bias ADR-001 warned against | Rejected |
| Full raw probability distribution across all conditions, uncurated | Maximally transparent | Information overload for a time-pressured clinician; buries the few genuinely relevant possibilities in noise | Rejected as impractical |
| Qualitative bands + inline evidence + persistent framing + inline data-quality flags (chosen) | Balances prioritization with honest uncertainty; directly counters anchoring bias; integrates ADR-002's signals at the point of decision, not a separate report | More complex to design and calibrate than a simple percentage list; qualitative bands could themselves be over-trusted over time if not periodically validated | Best tradeoff — directly operationalizes ADR-001 and ADR-002 rather than treating presentation as an afterthought |

## Consequences

**Positive:** Directly operationalizes ADR-001's intent (a ranked list that cannot be read as a
diagnosis) and ADR-002's honesty (data quality visible where it matters, not filed away).

**Negative / accepted tradeoffs:** Qualitative bands are harder to calibrate consistently than a
raw number and could themselves become over-trusted with repeated exposure — this is a residual
risk requiring ongoing UX validation, not something this ADR alone closes permanently.

## Validation

The Module 8 simulation will assert: every output object contains 2+ ranked items (never a bare
single item); every item carries a qualitative band and evidence field, never a raw percentage;
the non-diagnostic framing field is always present and non-empty; and any ADR-002 UNKNOWN/STALE
flag on the underlying data is always carried through to the per-item display, never dropped.