# ADR-002: Missing or Stale Regional Surveillance Data Is Reported as an Explicit UNKNOWN State — Never Interpolated Silently, Never Treated as Evidence of Low Resistance

**Status:** Accepted
**Date:** 2026-07-09
**Deciders:** System Architect (portfolio module)

## Context

WHO's GLASS system has grown substantially — participation has roughly quadrupled since 2016 to
127 countries and three territories enrolled by end of 2024, with 104 countries actually
submitting AMR data in 2023. That still leaves real, persistent regional gaps, concentrated in
Africa, the Americas, and parts of Asia, exactly where the 2025 GLASS report itself notes that
"resistance is more common and worsening... where health systems are weakest." This is not an
incidental gap: **the regions with the least surveillance capacity are, on the report's own
evidence, likely to have among the highest actual resistance burden.** Any system built on this
data must treat that correlation as a first-class architectural fact, not an edge case.

Two default behaviors are each independently dangerous here, and a naive implementation could
fall into either without anyone deciding to:

1. **Silently interpolating** a missing region's resistance data from a neighboring country or a
   global average, and presenting it with the same visual/statistical confidence as a directly
   reported measurement. This manufactures false certainty in exactly the places where the
   underlying reality is least known.
2. **Treating an absence of reported data as evidence of low or no resistance** — the single most
   dangerous possible default, since it inverts the actual relationship GLASS documents: weak
   surveillance correlates with higher resistance risk, not lower.

Given ADR-001's commitment to never overclaiming certainty, this module must resolve data absence
and staleness as deliberately as it resolves the diagnostic output itself.

## Decision

1. **Missing regional data is represented as an explicit `UNKNOWN` state**, structurally distinct
   from any measured resistance value — including a low one. `UNKNOWN` is never coerced into a
   default numeric value anywhere in the system.
2. **Every data point carries a report vintage** (the GLASS reporting cycle it came from). Data
   older than the most recently published reporting cycle is flagged as `STALE`, visibly distinct
   from current data — resistance patterns can shift meaningfully year over year (the 2025 report
   notes increases across more than 40% of monitored pathogen-antibiotic combinations between 2018
   and 2023, with relative annual increases of 5-15% in some combinations), so silently treating a
   several-year-old figure as current is its own form of false confidence.
3. **If a fallback estimate is shown for an `UNKNOWN` region at all** (e.g., a broader regional or
   global aggregate, clearly more useful than nothing for a clinician with zero local signal), it
   is tagged with a distinct provenance marker — "regional/global estimate, not local data" — and
   assigned a lower confidence weight than any directly reported measurement. It is never rendered
   identically to a direct measurement.
4. **A visible per-region coverage-confidence indicator** is maintained alongside every output, so
   a clinician in an under-represented region sees explicitly that their local context is thin —
   not simply a confident-looking result with no indication of its actual evidentiary weakness.

## Alternatives Considered

| Option | Pros | Cons | Why rejected |
|---|---|---|---|
| Silent interpolation from nearest available data (neighboring country or global average) | Always produces a number; simpler downstream logic | Manufactures false confidence precisely where the underlying health system — and likely the actual resistance burden — is weakest; the population most in need of an accurate signal gets the least reliable one, presented with unearned confidence | Rejected as actively dangerous, not merely imprecise |
| Treat missing data as "no resistance detected" / default to a low baseline | Simplest possible default handling | Inverts the exact relationship the source report documents — weak surveillance correlates with higher, not lower, resistance risk. This is the single most dangerous default available and must be explicitly rejected | Rejected outright |
| Exclude under-covered regions from the system entirely | Avoids presenting any potentially misleading information | Abandons the exact populations the report shows have the greatest need, and removes even honestly-labeled broader-context information that could still help | Rejected as overcorrection — swings from false certainty to zero support |
| Explicit `UNKNOWN`/`STALE` states, visible coverage-confidence indicators, and clearly-tagged, confidence-penalized fallback estimates only when used (chosen) | Preserves honesty about what is and isn't known; avoids both dangerous defaults; still offers the best available context without pretending it's local, current data | Adds real complexity to the data model and UI; the regions needing this system most will predictably show the least confident output — an equity tension this decision surfaces but cannot fully resolve | Best and only defensible option given the two rejected defaults are each independently dangerous |

## Consequences

**Positive:**
- Prevents the single most dangerous failure mode available in this domain: treating silence in
  the data as evidence of safety.
- Keeps the surveillance layer's honesty consistent with ADR-001's broader philosophy — this
  module does not overclaim certainty anywhere, including in its own input data, not just its
  output.

**Negative / accepted tradeoffs:**
- Meaningfully more complex data-handling logic: every value needs a provenance tag (direct /
  regional-fallback / global-fallback), a vintage, and a staleness check, rather than a single
  clean number.
- This decision is honest about what it cannot fix: the under-covered regions that need this
  system most will structurally receive its least confident output. That is a real,
  unresolved equity tension inherent to the underlying data-availability gap — better
  architecture surfaces it clearly rather than pretending to solve a problem that is
  fundamentally about surveillance investment, not software design.

## Validation

The Module 8 simulation will assert:

1. A region with no reported data returns an explicit `UNKNOWN` state — never a low numeric
   resistance value standing in for absence.
2. Data older than the current reporting-cycle threshold is flagged `STALE`, distinctly from
   current data, even when its underlying numeric value would otherwise look unremarkable.
3. A fallback regional/global estimate shown for an `UNKNOWN` region carries a distinct provenance
   tag and a strictly lower confidence weight than any directly reported measurement for that
   same query.