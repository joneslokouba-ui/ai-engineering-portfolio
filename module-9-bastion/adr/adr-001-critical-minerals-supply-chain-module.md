# ADR-001: Critical Minerals Supply Chain Resilience Module (Bastion)

## Status
Accepted

## Context
Critical minerals (rare earths, platinum group metals, battery metals,
refractory metals, and specialty minerals) underpin defense, energy
transition, and advanced manufacturing supply chains. Production is
highly concentrated in a small number of countries, creating acute
disruption risk. This module demonstrates an end-to-end system for:

1. Cataloging physical/chemical properties and downstream applications
   for critical minerals.
2. Quantifying supply concentration risk using the Herfindahl-Hirschman
   Index (HHI) per mineral.
3. Simulating discrete disruption events (export restriction, mine
   closure, geopolitical shock) and their cascading effects on
   application sectors, using discrete-event simulation.

This mirrors the architecture-first pattern established in Modules 5-8
(Sentinel, Sentry, Skylink, Vigil): ADR -> Mermaid diagram -> discrete-event
simulation -> Streamlit dashboard.

## Decision
Build "Bastion" as a self-contained Streamlit application with three
components:

- **Mineral Explorer** — static reference data (physical properties,
  chemical properties, primary applications) for ~16 critical minerals
  spanning REE, PGM, Battery, Refractory, and Specialty categories.
- **Supply Concentration Model** — HHI calculation from country-level
  production share data, producing a criticality/concentration matrix.
- **Disruption Simulator** — SimPy-based discrete-event simulation.
  A disruption event (chosen mineral + source country + severity) is
  injected at t=0. The simulation propagates reduced availability
  through affected application sectors over a configurable time horizon,
  with a stochastic recovery process (triangular distribution on
  recovery time, informed by historical analogues e.g. 2010 REE export
  quotas, 2023 Ge/Ga export controls).

## Data Sources & Honesty Boundary
As of this update, 5 of 16 minerals (Nd, Dy, Ga, Co, Li) have production-share
figures sourced directly from USGS Mineral Commodity Summaries 2025 (2024
production data), https://doi.org/10.3133/mcs2025. Nd and Dy use the
aggregate rare-earth mine production split by country, since USGS reports
REE production in aggregate rather than per-element; this is noted in-app
rather than presented as element-specific.

The remaining 11 minerals (Ge, Pt, Pd, Nb, Ta, W, Ti, Be, Sb, Re, Hf) retain
industry-consensus estimates broadly consistent with prior-year USGS data,
not individually re-verified line-by-line in this pass. Every mineral record
carries a `data_source` field ("MCS2025" or "estimate") and this is surfaced
directly in the dashboard UI (Mineral Explorer cards, Supply Concentration
table) rather than only documented here — a person using the tool should not
have to read the ADR to know which numbers are verified.

This module remains a systems/analytics demonstration, not a market
intelligence product, and figures will drift from real-world values over
time regardless of source.

## Consequences
- Positive: demonstrates domain crossover between geoscience background
  and simulation/dashboard engineering — a differentiator for both the
  hydrogeology and AI/ML tracks.
- Positive: reusable pattern — additional minerals or disruption
  scenarios can be added by extending `data/minerals_data.py` without
  touching simulation logic.
- Trade-off: static dataset means figures will drift from real-world
  values over time; documented as a known limitation, not hidden.

## Deployment Conventions (per established repo pattern)
- `sim/__init__.py` present preemptively.
- Module-specific `requirements.txt` at module root, pointed to
  explicitly in Streamlit Cloud Advanced Settings.
- All-hyphens ADR filename.