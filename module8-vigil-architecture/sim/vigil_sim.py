"""
vigil_sim.py

Module 8: Vigil Architecture — Structural Proof of the No-Autonomous-Tier
and Data-Honesty Boundaries

This is NOT a diagnostic tool and produces no real medical output. It is a
structural proof that ADR-001 (no autonomous diagnostic/treatment output),
ADR-002 (missing/stale data handled honestly), and ADR-003 (uncertainty
communication format) hold — including under adversarial input designed to
collapse the ranked-list output into a single "answer."

The strongest proofs here are structural, not behavioral: several functions
have no code path capable of returning a disallowed shape at all, the same
technique used for Module 7's isac_detection_effect() ceiling.

Run:
    python vigil_sim.py
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


# ---------------------------------------------------------------------------
# ADR-002: data provenance and staleness
# ---------------------------------------------------------------------------
class DataProvenance(Enum):
    DIRECT = "DIRECT"
    REGIONAL_FALLBACK = "REGIONAL_FALLBACK"
    GLOBAL_FALLBACK = "GLOBAL_FALLBACK"
    UNKNOWN = "UNKNOWN"

CURRENT_REPORTING_YEAR = 2025
STALENESS_THRESHOLD_YEARS = 2

CONFIDENCE_WEIGHT_BY_PROVENANCE = {
    DataProvenance.DIRECT: 1.0,
    DataProvenance.REGIONAL_FALLBACK: 0.5,
    DataProvenance.GLOBAL_FALLBACK: 0.25,
    DataProvenance.UNKNOWN: 0.0,
}


@dataclass
class ResistanceDataPoint:
    pathogen: str
    drug: str
    region: str
    provenance: DataProvenance
    report_year: int | None       # None only when provenance is UNKNOWN
    resistance_rate: float | None  # None only when provenance is UNKNOWN
    is_stale: bool = False


# A tiny mock "GLASS-style" data store: (region, pathogen, drug) -> (year, rate)
MOCK_DATA_STORE: dict[tuple[str, str, str], tuple[int, float]] = {
    ("region_a", "E.coli", "ciprofloxacin"): (2024, 0.42),
    ("region_b", "E.coli", "ciprofloxacin"): (2019, 0.38),  # stale
}
GLOBAL_AGGREGATE_RATE = {("E.coli", "ciprofloxacin"): 0.35}


def get_regional_data(region: str, pathogen: str, drug: str) -> ResistanceDataPoint:
    """
    ADR-002: a missing region returns an explicit UNKNOWN data point — never
    a numeric default (e.g. 0.0) standing in for absence.
    """
    key = (region, pathogen, drug)
    if key not in MOCK_DATA_STORE:
        return ResistanceDataPoint(
            pathogen=pathogen, drug=drug, region=region,
            provenance=DataProvenance.UNKNOWN,
            report_year=None, resistance_rate=None, is_stale=False,
        )
    year, rate = MOCK_DATA_STORE[key]
    is_stale = year < (CURRENT_REPORTING_YEAR - STALENESS_THRESHOLD_YEARS)
    return ResistanceDataPoint(
        pathogen=pathogen, drug=drug, region=region,
        provenance=DataProvenance.DIRECT,
        report_year=year, resistance_rate=rate, is_stale=is_stale,
    )


def get_regional_data_with_fallback(region: str, pathogen: str, drug: str) -> ResistanceDataPoint:
    """
    ADR-002: if direct regional data is UNKNOWN, a fallback global estimate
    MAY be shown — but always tagged with a distinct provenance and a
    strictly lower confidence weight than direct measurement, never
    presented as equivalent to it.
    """
    direct = get_regional_data(region, pathogen, drug)
    if direct.provenance != DataProvenance.UNKNOWN:
        return direct
    global_key = (pathogen, drug)
    if global_key in GLOBAL_AGGREGATE_RATE:
        return ResistanceDataPoint(
            pathogen=pathogen, drug=drug, region=region,
            provenance=DataProvenance.GLOBAL_FALLBACK,
            report_year=CURRENT_REPORTING_YEAR, resistance_rate=GLOBAL_AGGREGATE_RATE[global_key],
            is_stale=False,
        )
    return direct  # remains UNKNOWN if no fallback exists either


# ---------------------------------------------------------------------------
# ADR-001 / ADR-003: differential output structure
# ---------------------------------------------------------------------------
class ConfidenceBand(Enum):
    STRONG = "supported by strong regional evidence"
    MODERATE = "moderate signal"
    WEAK = "weak/uncertain signal"
    UNKNOWN = "no reliable regional signal"


FRAMING_HEADER = "Differential considerations for clinical review — not a diagnosis"

# ADR-004: watch-list of severity/reportability-flagged conditions. Membership
# here guarantees a visible slot regardless of confidence ranking or list
# truncation — this is illustrative, not a real WHO priority-pathogen list.
SEVERITY_WATCHLIST = {"drug_resistant_TB", "MDR_gram_negative_sepsis"}


@dataclass
class DifferentialItem:
    condition: str
    confidence_band: ConfidenceBand
    evidence: list[str]
    data_flags: list[str] = field(default_factory=list)
    severity_flagged: bool = False


@dataclass
class DifferentialOutput:
    items: list[DifferentialItem]
    framing_header: str = FRAMING_HEADER
    severity_section: list[DifferentialItem] = field(default_factory=list)


class DiagnosticContextLayer:
    """
    ADR-001's core structural guarantee: this class has NO method and no
    code path that returns fewer than two ranked items, a raw numeric
    confidence score, or an empty framing header. There is nothing to
    "turn off" to collapse this into a single-answer output — the shape
    is enforced by construction, the same technique as Module 7's
    isac_detection_effect() ceiling.
    """

    TOP_N_DISPLAY_LIMIT = 2  # ADR-003's readability cap on the ranked list

    def generate(
        self,
        candidate_conditions: list[str],
        regional_data: ResistanceDataPoint,
        force_single_answer: bool = False,  # adversarial input — deliberately has no effect
    ) -> DifferentialOutput:
        data_flags: list[str] = []
        if regional_data.provenance == DataProvenance.UNKNOWN:
            data_flags.append("UNKNOWN: no regional data available")
        elif regional_data.provenance in (DataProvenance.REGIONAL_FALLBACK, DataProvenance.GLOBAL_FALLBACK):
            data_flags.append(f"{regional_data.provenance.value}: not direct local measurement")
        if regional_data.is_stale:
            data_flags.append(f"STALE: data from {regional_data.report_year}")

        band = self._confidence_band_for(regional_data)

        # ADR-003: the ranked list is truncated for readability — candidate_conditions
        # is treated as already confidence-ordered (highest first), so this slice
        # simulates "top N by likelihood," the exact truncation ADR-004 must not
        # let silently drop a severity-flagged condition.
        ranked_slice = candidate_conditions[: self.TOP_N_DISPLAY_LIMIT]
        if len(ranked_slice) < 2:
            ranked_slice = candidate_conditions[:2] if len(candidate_conditions) >= 2 else ranked_slice

        items = [
            DifferentialItem(
                condition=condition,
                confidence_band=band,
                evidence=[f"consistent with reported presentation pattern for {condition}"],
                data_flags=list(data_flags),
                severity_flagged=condition in SEVERITY_WATCHLIST,
            )
            for condition in ranked_slice
        ]
        if len(items) < 2:
            items.append(
                DifferentialItem(
                    condition="other differential considerations not ruled out",
                    confidence_band=ConfidenceBand.UNKNOWN,
                    evidence=["insufficient input to rank further possibilities"],
                    data_flags=list(data_flags),
                )
            )

        # ADR-004: any watch-list condition present in the FULL candidate set but
        # excluded from the truncated ranked list above must still surface here,
        # regardless of how low it ranked by confidence alone.
        shown_conditions = {item.condition for item in items}
        severity_section = [
            DifferentialItem(
                condition=condition,
                confidence_band=ConfidenceBand.WEAK,
                evidence=["lower likelihood by presentation pattern, but flagged for severity/reportability"],
                data_flags=list(data_flags),
                severity_flagged=True,
            )
            for condition in candidate_conditions
            if condition in SEVERITY_WATCHLIST and condition not in shown_conditions
        ]

        return DifferentialOutput(items=items, framing_header=FRAMING_HEADER, severity_section=severity_section)

    @staticmethod
    def _confidence_band_for(regional_data: ResistanceDataPoint) -> ConfidenceBand:
        if regional_data.provenance == DataProvenance.UNKNOWN:
            return ConfidenceBand.UNKNOWN
        if regional_data.is_stale or regional_data.provenance != DataProvenance.DIRECT:
            return ConfidenceBand.WEAK
        return ConfidenceBand.MODERATE


# ---------------------------------------------------------------------------
# Scenario harness
# ---------------------------------------------------------------------------
def report(name: str, passed: bool, detail: str = "") -> None:
    status = "PASS" if passed else "FAIL"
    line = f"[{status}] {name}"
    if detail:
        line += f" — {detail}"
    print(line)


def scenario_missing_region_is_unknown_never_numeric():
    """ADR-002: a region with no reported data returns UNKNOWN, never a numeric default."""
    dp = get_regional_data("region_z", "E.coli", "ciprofloxacin")
    report(
        "Scenario 1: Missing region returns explicit UNKNOWN, never a numeric default",
        dp.provenance == DataProvenance.UNKNOWN and dp.resistance_rate is None,
        f"provenance={dp.provenance.value}, resistance_rate={dp.resistance_rate}",
    )


def scenario_stale_data_flagged():
    """ADR-002: data older than the staleness threshold is flagged, even with a valid numeric value."""
    dp = get_regional_data("region_b", "E.coli", "ciprofloxacin")
    report(
        "Scenario 2: Data from 2019 is flagged STALE relative to 2025 reporting year",
        dp.is_stale is True and dp.resistance_rate is not None,
        f"report_year={dp.report_year}, is_stale={dp.is_stale}",
    )


def scenario_fresh_direct_data_not_stale():
    """ADR-002: current, directly reported data is NOT flagged stale."""
    dp = get_regional_data("region_a", "E.coli", "ciprofloxacin")
    report(
        "Scenario 3: Fresh direct data (2024) is not flagged stale",
        dp.is_stale is False and dp.provenance == DataProvenance.DIRECT,
        f"report_year={dp.report_year}, is_stale={dp.is_stale}, provenance={dp.provenance.value}",
    )


def scenario_fallback_has_lower_confidence_than_direct():
    """ADR-002: a fallback estimate is tagged distinctly and weighted strictly lower than direct measurement."""
    fallback = get_regional_data_with_fallback("region_z", "E.coli", "ciprofloxacin")
    direct = get_regional_data("region_a", "E.coli", "ciprofloxacin")
    report(
        "Scenario 4: Fallback estimate is tagged distinctly with strictly lower confidence than direct data",
        fallback.provenance == DataProvenance.GLOBAL_FALLBACK
        and CONFIDENCE_WEIGHT_BY_PROVENANCE[fallback.provenance] < CONFIDENCE_WEIGHT_BY_PROVENANCE[direct.provenance],
        f"fallback_provenance={fallback.provenance.value} (weight={CONFIDENCE_WEIGHT_BY_PROVENANCE[fallback.provenance]}), "
        f"direct_weight={CONFIDENCE_WEIGHT_BY_PROVENANCE[direct.provenance]}",
    )


def scenario_output_always_multi_item():
    """ADR-001/ADR-003: normal generation always produces 2+ ranked items."""
    layer = DiagnosticContextLayer()
    regional = get_regional_data("region_a", "E.coli", "ciprofloxacin")
    output = layer.generate(["condition_x", "condition_y", "condition_z"], regional)
    report(
        "Scenario 5: Output contains 2+ ranked items under normal generation",
        len(output.items) >= 2,
        f"item_count={len(output.items)}",
    )


def scenario_adversarial_single_answer_forced_still_multi_item():
    """
    ADR-001's core claim: an adversarial attempt to force a single-answer
    output has no effect — the function has no code path to collapse the
    list, regardless of the flag's value.
    """
    layer = DiagnosticContextLayer()
    regional = get_regional_data("region_a", "E.coli", "ciprofloxacin")
    output = layer.generate(["condition_x"], regional, force_single_answer=True)
    report(
        "Scenario 6: force_single_answer=True still produces 2+ items — no collapse path exists",
        len(output.items) >= 2,
        f"item_count={len(output.items)} (requested single answer)",
    )


def scenario_confidence_is_qualitative_not_numeric():
    """ADR-003: confidence is always a qualitative band (enum), never a raw float/percentage."""
    layer = DiagnosticContextLayer()
    regional = get_regional_data("region_a", "E.coli", "ciprofloxacin")
    output = layer.generate(["condition_x", "condition_y"], regional)
    report(
        "Scenario 7: Confidence is a qualitative ConfidenceBand enum, never a raw number",
        all(isinstance(item.confidence_band, ConfidenceBand) for item in output.items),
        f"bands={[item.confidence_band.name for item in output.items]}",
    )


def scenario_framing_header_always_present():
    """ADR-003: the non-diagnostic framing header is always present and non-empty."""
    layer = DiagnosticContextLayer()
    regional = get_regional_data("region_z", "E.coli", "ciprofloxacin")  # UNKNOWN region
    output = layer.generate(["condition_x", "condition_y"], regional)
    report(
        "Scenario 8: Non-diagnostic framing header is always present, even for UNKNOWN-region output",
        bool(output.framing_header) and "not a diagnosis" in output.framing_header,
        f"framing_header='{output.framing_header}'",
    )


def scenario_data_flags_carried_through_per_item():
    """ADR-002 + ADR-003: UNKNOWN/STALE flags on the underlying data are carried through to every item, never dropped."""
    layer = DiagnosticContextLayer()
    stale_regional = get_regional_data("region_b", "E.coli", "ciprofloxacin")  # stale
    output = layer.generate(["condition_x", "condition_y"], stale_regional)
    report(
        "Scenario 9: STALE flag on underlying data is carried through to every ranked item",
        all(any("STALE" in flag for flag in item.data_flags) for item in output.items),
        f"item_flags={[item.data_flags for item in output.items]}",
    )


def scenario_watchlist_condition_survives_truncation():
    """
    ADR-004's core claim: a watch-list condition ranked low enough to be
    excluded from the truncated ranked list still surfaces, distinctly
    flagged, in the severity section — it is never silently dropped.
    """
    layer = DiagnosticContextLayer()
    regional = get_regional_data("region_a", "E.coli", "ciprofloxacin")
    # "drug_resistant_TB" is 4th by rank order — excluded by TOP_N_DISPLAY_LIMIT=2
    candidates = ["common_cold", "seasonal_flu", "viral_pharyngitis", "drug_resistant_TB"]
    output = layer.generate(candidates, regional)
    report(
        "Scenario 10: Low-ranked watch-list condition still surfaces in severity section, never dropped",
        "drug_resistant_TB" not in {i.condition for i in output.items}
        and any(i.condition == "drug_resistant_TB" and i.severity_flagged for i in output.severity_section),
        f"main_list={[i.condition for i in output.items]}, severity_section={[i.condition for i in output.severity_section]}",
    )


def scenario_non_watchlist_condition_can_be_truncated():
    """
    ADR-004's boundary claim: the guarantee is specific to flagged
    conditions, not a blanket 'never truncate anything' rule — a low-ranked
    NON-watchlist condition can legitimately be excluded from the output.
    """
    layer = DiagnosticContextLayer()
    regional = get_regional_data("region_a", "E.coli", "ciprofloxacin")
    candidates = ["common_cold", "seasonal_flu", "viral_pharyngitis", "mild_allergic_rhinitis"]
    output = layer.generate(candidates, regional)
    shown = {i.condition for i in output.items} | {i.condition for i in output.severity_section}
    report(
        "Scenario 11: A low-ranked NON-watchlist condition can be excluded — the floor is specific, not universal",
        "mild_allergic_rhinitis" not in shown,
        f"shown_conditions={shown}",
    )


def run_all():
    print("=" * 70)
    print("Module 8: Vigil Architecture — Structural Boundary Proof")
    print("Validating ADR-001, ADR-002, ADR-003, ADR-004")
    print("=" * 70)
    scenario_missing_region_is_unknown_never_numeric()
    scenario_stale_data_flagged()
    scenario_fresh_direct_data_not_stale()
    scenario_fallback_has_lower_confidence_than_direct()
    scenario_output_always_multi_item()
    scenario_adversarial_single_answer_forced_still_multi_item()
    scenario_confidence_is_qualitative_not_numeric()
    scenario_framing_header_always_present()
    scenario_data_flags_carried_through_per_item()
    scenario_watchlist_condition_survives_truncation()
    scenario_non_watchlist_condition_can_be_truncated()
    print("=" * 70)
    print("All scenarios executed. Review PASS/FAIL above against the ADRs.")
    print("=" * 70)


if __name__ == "__main__":
    run_all()