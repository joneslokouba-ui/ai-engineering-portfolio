# ADR-004: Severity-Flagged and WHO-Reportable Conditions Are Never Omitted or Buried by Confidence Ranking Alone

**Status:** Accepted
**Date:** 2026-07-09
**Deciders:** System Architect (portfolio module)

## Context

ADR-003 established a confidence-ranked list, kept short (2-3 items) to avoid the information
overload and alert fatigue that undermine real clinical decision support. That design has a
specific, realistic failure mode: **confidence ranking optimizes for "most likely," not "most
dangerous to miss."** A drug-resistant pathogen or a WHO-reportable, epidemic-prone disease can be
statistically less common than an ordinary explanation for a given presentation, while being far
more consequential if missed — both for the individual patient (an ineffective treatment path
while a resistant infection progresses) and for public health (delayed reporting of a
transmissible, reportable disease). A truncated, likelihood-only list can silently drop exactly
the possibility that matters most, precisely because it ranks low on probability alone.

This is a well-established principle in real clinical safety practice — "can't-miss diagnoses"
are tracked separately from probability-ranked differentials for exactly this reason. Confidence
and consequence are two different axes; a single ranked list conflates them.

## Decision

The system maintains two separate, structurally distinct outputs:

1. **The confidence-ranked differential list** (per ADR-003) — likelihood-ordered, kept short for
   readability, exactly as already decided.
2. **A separate, always-visible severity/reportability section**, independent of ranking or list
   truncation. Any condition on a maintained watch-list — current WHO-priority drug-resistant
   pathogens and WHO-reportable/epidemic-prone diseases — that is even plausibly consistent with
   the input is guaranteed a visible slot here, explicitly labeled "lower likelihood, high
   severity — not excluded," regardless of where it would fall in the confidence-ranked list.

ADR-003's "2-3 items" is a floor for the likelihood-ranked list's readability, never a cap that
can silently exclude a flagged severity item from the output entirely.

## Alternatives Considered

| Option | Pros | Cons | Why rejected |
|---|---|---|---|
| Pure confidence-ranked list only, truncated for readability (status quo) | Simplest, avoids list clutter | A rare-but-severe or reportable condition can be silently dropped exactly when catching it matters most | Rejected — the single most dangerous omission this module could make |
| Always show every plausible condition, unranked, no truncation ever | Guarantees nothing severe is hidden | Reintroduces the information-overload problem ADR-003 explicitly rejected; the important item gets buried among common ones anyway, defeating the purpose | Rejected — same alert-fatigue failure ADR-003 already ruled out |
| Two-axis output: ranked list (ADR-003) + separate always-visible severity/reportability section, independent of truncation (chosen) | Preserves the readable ranked list while guaranteeing high-consequence possibilities are never silently dropped; separates "how likely" from "how dangerous to miss" | Requires maintaining and periodically updating a watch-list tied to current WHO guidance; needs careful UI design so this section doesn't itself become a new anchoring risk | Best tradeoff — closes the omission gap without recreating the overload problem |

## Consequences

**Positive:** Closes a specific, realistic failure mode where ranking-for-likelihood silently
suppresses ranking-for-consequence. Extends this module's honesty principle — already applied to
data provenance (ADR-002) and confidence framing (ADR-003) — to omission itself: the system must
be honest about what it *doesn't* show, not just careful about how it frames what it does.

**Negative / accepted tradeoffs:** Requires ongoing content governance — the watch-list must track
current WHO priority-pathogen and reportable-disease guidance, which changes over time. Introduces
a second UI section that itself must be carefully framed, or it risks becoming a new anchoring
point — a design problem this ADR raises but does not fully resolve.

## Validation

The Module 8 simulation will assert: a watch-list condition that ranks low by confidence still
appears in the output, distinctly flagged, never silently excluded from a truncated list — and,
to prove the guarantee is deliberate rather than accidental, a non-watch-list condition at the
same low confidence level *can* be excluded from the general list, showing the floor applies
specifically to flagged severity, not everything indiscriminately.