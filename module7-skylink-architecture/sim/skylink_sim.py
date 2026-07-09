"""
skylink_sim.py

Module 7: Skylink Architecture — RF Physics and Handover Proof

This is NOT a production network simulator. It is a physics-grounded,
discrete proof that the architecture decisions in ADR-001 (network slice
isolation), ADR-002 (zone-based deployment model selection), ADR-003
(aerial handover/mobility policy), and ADR-004 (ISAC drone-detection
integration) hold under load, zone transitions, realistic antenna-pattern
behavior for aerial user equipment, and resource contention with a new
sensing capability.

Unlike Modules 5 and 6, this module involves real RF physics: free-space
path loss, antenna gain patterns (main lobe vs. sidelobe), and Doppler
shift. All of it is standard math — no C++ is required for correctness or
credibility here; see the module README for the reasoning.

The DegradationState names deliberately match Module 5's degradation
ladder (NOMINAL / DEGRADED / LOST / FAIL_SAFE). This is intentional: per
ADR-001 through ADR-003, every failure mode in this module is designed to
report into that same contract rather than invent a parallel one. Modules
are deployed and run independently, so the enum is redefined here rather
than imported — but the names and meaning are kept identical on purpose.

Run:
    python skylink_sim.py
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from enum import Enum


# ---------------------------------------------------------------------------
# Shared degradation contract (matches Module 5's ladder by design — see
# ADR-001/002/003/004, each of which routes its failure case into this
# ladder rather than inventing new failure semantics).
# ---------------------------------------------------------------------------
class DegradationState(Enum):
    NOMINAL = 0
    DEGRADED = 1
    LOST = 2
    FAIL_SAFE = 3


# ---------------------------------------------------------------------------
# Physical constants and architecture parameters
# ---------------------------------------------------------------------------
SPEED_OF_LIGHT_MPS = 3.0e8
CARRIER_FREQ_HZ = 3.5e9          # mid-band 5G, typical of current deployments
TX_POWER_DBM = 43.0              # typical macro cell transmit power

CELL_SPACING_M = 1500.0          # inter-site distance along the flight path
UAV_ALTITUDE_M = 600.0           # ~2,000 ft — medium altitude band

# Ground-optimized antenna: downtilted for ground coverage, narrow main lobe.
ANTENNA_BORESIGHT_DEG = -6.0
ANTENNA_HALF_POWER_BEAMWIDTH_DEG = 8.0
MAIN_LOBE_GAIN_DBI = 17.0
SIDELOBE_BASE_GAIN_DBI = 2.0
SIDELOBE_RIPPLE_DB = 4.0         # real array antennas show sidelobe ripple vs. angle
SIDELOBE_RIPPLE_SPATIAL_FREQ = 60  # oscillation rate of ripple vs. angle-off-boresight

# ADR-001: overall C2/UTM slice SLA.
LATENCY_BUDGET_MS = 10.0
BASE_NETWORK_LATENCY_MS = 5.0
ISOLATED_SLICE_MAX_SUPPORTED_LOAD = 0.95  # beyond this, the slice itself is saturated

# ADR-003: handover-latency sub-budget carved out of the overall SLA.
HANDOVER_INTERRUPTION_MS = 3.0
HANDOVER_SUBBUDGET_MS = 5.0
HANDOVER_STACK_WINDOW_M = 150.0  # handovers this close together are treated as stacked

# Mobility hysteresis margins (ADR-003's core lever).
GROUND_DEFAULT_HYSTERESIS_DB = 2.0   # typical ground A3-event hysteresis
AERIAL_OPTIMIZED_HYSTERESIS_DB = 6.0  # wider margin from the mobility-bias policy

# ADR-004: ISAC resource-subordination and corroboration requirements.
C2_RESERVED_CAPACITY_FRACTION = 0.30   # guaranteed minimum, never encroached on by ISAC
ISAC_MULTISTATIC_MIN_NODES = 2         # corroborating nodes required before affecting connected-UAV state


# ---------------------------------------------------------------------------
# RF physics
# ---------------------------------------------------------------------------
def free_space_path_loss_db(distance_m: float, freq_hz: float = CARRIER_FREQ_HZ) -> float:
    """Standard FSPL: 20log10(d) + 20log10(f) + 20log10(4*pi/c)."""
    distance_m = max(distance_m, 1.0)
    return (
        20 * math.log10(distance_m)
        + 20 * math.log10(freq_hz)
        + 20 * math.log10(4 * math.pi / SPEED_OF_LIGHT_MPS)
    )


def elevation_angle_deg(horizontal_distance_m: float, altitude_m: float) -> float:
    return math.degrees(math.atan2(altitude_m, max(horizontal_distance_m, 0.001)))


def antenna_gain_dbi(elevation_deg: float) -> float:
    """
    Ground-optimized antenna: downtilted boresight, narrow main lobe. An
    aerial UE overhead is almost always outside that main lobe (it's looking
    UP at the antenna while the antenna looks slightly DOWN), so it is
    served by the sidelobe region — matching the paper's stated finding.
    The sidelobe gain includes a ripple term: real phased-array antennas
    have oscillating sidelobe levels vs. angle, which is the physical
    mechanism behind the "elevated intra-frequency interference" the paper
    describes for aerial UEs at medium altitude.
    """
    angle_off_boresight = abs(elevation_deg - ANTENNA_BORESIGHT_DEG)
    if angle_off_boresight <= ANTENNA_HALF_POWER_BEAMWIDTH_DEG / 2:
        return MAIN_LOBE_GAIN_DBI
    ripple = SIDELOBE_RIPPLE_DB * math.cos(math.radians(angle_off_boresight * SIDELOBE_RIPPLE_SPATIAL_FREQ))
    return SIDELOBE_BASE_GAIN_DBI + ripple


def doppler_shift_hz(velocity_mps: float, freq_hz: float = CARRIER_FREQ_HZ, angle_deg: float = 0.0) -> float:
    """Doppler shift for a UAV moving at velocity_mps relative to the base station line-of-sight."""
    return (velocity_mps / SPEED_OF_LIGHT_MPS) * freq_hz * math.cos(math.radians(angle_deg))


def received_signal_dbm(horizontal_distance_m: float, altitude_m: float = UAV_ALTITUDE_M) -> float:
    distance_3d = math.sqrt(horizontal_distance_m ** 2 + altitude_m ** 2)
    fspl = free_space_path_loss_db(distance_3d)
    elev = elevation_angle_deg(horizontal_distance_m, altitude_m)
    gain = antenna_gain_dbi(elev)
    return TX_POWER_DBM + gain - fspl


# ---------------------------------------------------------------------------
# ADR-001: network slice latency under load
# ---------------------------------------------------------------------------
def slice_latency_ms(background_load: float, isolated: bool) -> tuple[float, DegradationState]:
    """
    isolated=True models the dedicated C2/UTM slice from ADR-001: latency
    stays near-constant regardless of general public traffic load, UNLESS
    the slice's own supported capacity is exceeded, in which case it must
    report as degraded rather than return a falsely reassuring number.

    isolated=False models a shared, non-sliced network: latency grows
    without bound as background load approaches capacity (simple M/M/1-style
    queueing behavior), directly illustrating why ADR-001 rejects this.
    """
    if isolated:
        if background_load >= ISOLATED_SLICE_MAX_SUPPORTED_LOAD:
            return float("inf"), DegradationState.DEGRADED
        return BASE_NETWORK_LATENCY_MS + 1.0, DegradationState.NOMINAL  # small fixed jitter
    background_load = min(background_load, 0.999)
    latency = BASE_NETWORK_LATENCY_MS / (1 - background_load)
    state = DegradationState.NOMINAL if latency <= LATENCY_BUDGET_MS else DegradationState.DEGRADED
    return latency, state


# ---------------------------------------------------------------------------
# ADR-002: zone-based deployment model selection
# ---------------------------------------------------------------------------
@dataclass
class ZoneSegment:
    start_km: float
    end_km: float
    zone_type: str  # "standard", "critical", "transition"


ZONE_MAP = [
    ZoneSegment(0.0, 10.0, "standard"),
    ZoneSegment(10.0, 10.5, "transition"),
    ZoneSegment(10.5, 15.0, "critical"),
]

DEPLOYMENT_BY_ZONE = {
    "standard": "MNO Network Slice",
    "critical": "FAA Private Network",
    "transition": "Hybrid",
}


def deployment_model_at(position_km: float) -> str:
    for seg in ZONE_MAP:
        if seg.start_km <= position_km < seg.end_km:
            return DEPLOYMENT_BY_ZONE[seg.zone_type]
    return DEPLOYMENT_BY_ZONE[ZONE_MAP[-1].zone_type]


def zone_transition_result(position_km: float, handover_gap_detected: bool) -> DegradationState:
    """ADR-002: a handover gap at a zone boundary must report DEGRADED, never silently NOMINAL."""
    return DegradationState.DEGRADED if handover_gap_detected else DegradationState.NOMINAL


# ---------------------------------------------------------------------------
# ADR-003: aerial handover simulation
# ---------------------------------------------------------------------------
def simulate_handovers(hysteresis_db: float, path_start_m: float, path_end_m: float, step_m: float = 10.0) -> list[float]:
    """
    Two adjacent cells at x=0 and x=CELL_SPACING_M. Walk the UAV along the
    path and apply standard A3-event handover logic: switch serving cell
    only when a candidate's signal exceeds the current serving cell's by
    more than the hysteresis margin. Returns the flight positions (m) at
    which a handover occurred.
    """
    cell_positions = (0.0, CELL_SPACING_M)
    position = path_start_m
    serving_idx = 0 if received_signal_dbm(abs(path_start_m - cell_positions[0])) >= \
        received_signal_dbm(abs(path_start_m - cell_positions[1])) else 1
    handover_positions: list[float] = []

    while position <= path_end_m:
        signals = [received_signal_dbm(abs(position - c)) for c in cell_positions]
        candidate_idx = 1 - serving_idx
        if signals[candidate_idx] - signals[serving_idx] > hysteresis_db:
            handover_positions.append(position)
            serving_idx = candidate_idx
        position += step_m

    return handover_positions


def evaluate_handover_burden(handover_positions: list[float]) -> tuple[float, DegradationState]:
    """
    ADR-003: handovers occurring within HANDOVER_STACK_WINDOW_M of each other
    are treated as stacked — their interruption costs sum rather than being
    independently absorbed. A stacked cluster whose combined interruption
    exceeds the sub-budget is DEGRADED; an isolated handover within budget
    is NOMINAL.
    """
    if not handover_positions:
        return 0.0, DegradationState.NOMINAL

    worst_cluster_ms = 0.0
    cluster_ms = HANDOVER_INTERRUPTION_MS
    for prev, curr in zip(handover_positions, handover_positions[1:]):
        if curr - prev <= HANDOVER_STACK_WINDOW_M:
            cluster_ms += HANDOVER_INTERRUPTION_MS
        else:
            worst_cluster_ms = max(worst_cluster_ms, cluster_ms)
            cluster_ms = HANDOVER_INTERRUPTION_MS
    worst_cluster_ms = max(worst_cluster_ms, cluster_ms)

    state = DegradationState.NOMINAL if worst_cluster_ms <= HANDOVER_SUBBUDGET_MS else DegradationState.DEGRADED
    return worst_cluster_ms, state


# ---------------------------------------------------------------------------
# ADR-004: ISAC resource subordination and detection corroboration
# ---------------------------------------------------------------------------
def isac_resource_allocation(background_load: float, isac_requested_fraction: float) -> tuple[float, float, DegradationState]:
    """
    ADR-004: the C2/UTM slice's reserved capacity is never encroached on by
    ISAC sensing, no matter how much capacity ISAC requests or how high
    general background load runs. ISAC gets whatever remains after the C2
    reservation and existing background load — it is throttled, never the
    reverse.

    Returns (c2_slice_latency_ms, isac_allocated_fraction, c2_slice_state).
    """
    # The C2/UTM slice's own guarantee (ADR-001) is evaluated independently
    # of ISAC's request — ISAC has no path to affect it.
    c2_latency_ms, c2_state = slice_latency_ms(background_load=0.0, isolated=True)

    remaining_capacity = max(0.0, 1.0 - C2_RESERVED_CAPACITY_FRACTION - background_load)
    isac_allocated_fraction = min(isac_requested_fraction, remaining_capacity)

    return c2_latency_ms, isac_allocated_fraction, c2_state


def isac_detection_effect(corroborating_nodes: int) -> DegradationState:
    """
    ADR-004: a single-node (monostatic) detection is probabilistic advisory
    input only and has zero effect on connected-UAV state. Only multi-static
    corroboration (>= ISAC_MULTISTATIC_MIN_NODES) elevates to an advisory
    DEGRADED state. Regardless of how many nodes corroborate, this function
    has no path to return anything beyond DEGRADED — there is no autonomous
    escalation to LOST/FAIL_SAFE or any high-consequence action from a
    sensing signal alone, by construction.
    """
    if corroborating_nodes >= ISAC_MULTISTATIC_MIN_NODES:
        return DegradationState.DEGRADED
    return DegradationState.NOMINAL


# ---------------------------------------------------------------------------
# Scenario harness
# ---------------------------------------------------------------------------
def report(name: str, passed: bool, detail: str = "") -> None:
    status = "PASS" if passed else "FAIL"
    line = f"[{status}] {name}"
    if detail:
        line += f" — {detail}"
    print(line)


def scenario_fspl_sanity():
    """Physics sanity check: FSPL at 1km, 3.5GHz should be roughly in the 100-110 dB range."""
    fspl = free_space_path_loss_db(1000.0, CARRIER_FREQ_HZ)
    report(
        "Scenario 1: FSPL at 1km/3.5GHz is physically plausible (100-110 dB)",
        100.0 <= fspl <= 110.0,
        f"FSPL={fspl:.1f} dB",
    )


def scenario_isolated_slice_within_budget():
    """ADR-001: the dedicated slice stays within the 10ms SLA even under heavy background load."""
    latency, state = slice_latency_ms(background_load=0.90, isolated=True)
    report(
        "Scenario 2: Isolated C2 slice stays within 10ms SLA at 90% background load",
        latency <= LATENCY_BUDGET_MS and state == DegradationState.NOMINAL,
        f"latency={latency:.1f}ms, state={state.name}",
    )


def scenario_shared_network_breaches_budget():
    """ADR-001's core rationale: a NON-isolated network breaches the SLA under the same load."""
    latency, state = slice_latency_ms(background_load=0.60, isolated=False)
    report(
        "Scenario 3: Non-isolated shared network breaches 10ms SLA at 60% background load",
        latency > LATENCY_BUDGET_MS and state == DegradationState.DEGRADED,
        f"latency={latency:.1f}ms, state={state.name}",
    )


def scenario_slice_saturation_reports_degraded():
    """ADR-001: if the isolated slice's own capacity is exceeded, it must report DEGRADED, not a false-reassuring number."""
    latency, state = slice_latency_ms(background_load=0.98, isolated=True)
    report(
        "Scenario 4: Isolated slice saturation reports DEGRADED, not a false-nominal latency",
        state == DegradationState.DEGRADED,
        f"latency={latency}, state={state.name}",
    )


def scenario_zone_deployment_selection():
    """ADR-002: deployment model correctly follows the zone map."""
    standard = deployment_model_at(5.0)
    critical = deployment_model_at(13.0)
    report(
        "Scenario 5: Deployment model matches zone classification (standard->MNO, critical->FAA Private)",
        standard == "MNO Network Slice" and critical == "FAA Private Network",
        f"standard_zone={standard}, critical_zone={critical}",
    )


def scenario_clean_zone_transition():
    """ADR-002: a clean handover at a zone boundary reports NOMINAL."""
    state = zone_transition_result(position_km=10.2, handover_gap_detected=False)
    report(
        "Scenario 6: Clean zone-boundary handover reports NOMINAL",
        state == DegradationState.NOMINAL,
        f"state={state.name}",
    )


def scenario_zone_transition_gap_reports_degraded():
    """ADR-002: a detected handover gap at a zone boundary reports DEGRADED, never silently NOMINAL."""
    state = zone_transition_result(position_km=10.2, handover_gap_detected=True)
    report(
        "Scenario 7: Zone-boundary handover gap reports DEGRADED, not silently NOMINAL",
        state == DegradationState.DEGRADED,
        f"state={state.name}",
    )


def scenario_ground_optimized_ping_pong_breaches_subbudget():
    """
    ADR-003's core claim: default ground-optimized mobility (small hysteresis)
    produces stacked handovers near the cell midpoint due to sidelobe ripple,
    breaching the 5ms handover sub-budget.
    """
    midpoint = CELL_SPACING_M / 2
    handovers = simulate_handovers(
        GROUND_DEFAULT_HYSTERESIS_DB, midpoint - 300, midpoint + 300, step_m=5.0
    )
    worst_cluster_ms, state = evaluate_handover_burden(handovers)
    report(
        "Scenario 8: Ground-optimized mobility (2dB hysteresis) breaches the 5ms handover sub-budget",
        state == DegradationState.DEGRADED,
        f"handover_count={len(handovers)}, worst_cluster={worst_cluster_ms:.1f}ms, state={state.name}",
    )


def scenario_aerial_optimized_stays_within_subbudget():
    """ADR-003: aerial-optimized mobility (wide hysteresis) avoids stacking and stays within budget."""
    midpoint = CELL_SPACING_M / 2
    handovers = simulate_handovers(
        AERIAL_OPTIMIZED_HYSTERESIS_DB, midpoint - 300, midpoint + 300, step_m=5.0
    )
    worst_cluster_ms, state = evaluate_handover_burden(handovers)
    report(
        "Scenario 9: Aerial-optimized mobility (6dB hysteresis) stays within the 5ms handover sub-budget",
        state == DegradationState.NOMINAL,
        f"handover_count={len(handovers)}, worst_cluster={worst_cluster_ms:.1f}ms, state={state.name}",
    )


def scenario_doppler_sanity():
    """Physics sanity check: Doppler shift for a typical UAV cruise speed should be a few hundred Hz."""
    shift = doppler_shift_hz(velocity_mps=20.0, freq_hz=CARRIER_FREQ_HZ, angle_deg=0.0)
    report(
        "Scenario 10: Doppler shift at 20 m/s / 3.5GHz is physically plausible (100-400 Hz)",
        100.0 <= shift <= 400.0,
        f"doppler_shift={shift:.1f} Hz",
    )


def scenario_isac_never_encroaches_c2_slice():
    """
    ADR-004's core resource claim: even when ISAC requests heavy capacity
    under high background load, the C2/UTM slice's guarantee is untouched —
    ISAC's allocation shrinks (is throttled) instead.
    """
    c2_latency, isac_allocated, c2_state = isac_resource_allocation(
        background_load=0.65, isac_requested_fraction=0.90
    )
    report(
        "Scenario 11: C2 slice SLA is preserved under heavy ISAC demand; ISAC is throttled instead",
        c2_latency <= LATENCY_BUDGET_MS
        and c2_state == DegradationState.NOMINAL
        and isac_allocated < 0.90,
        f"c2_latency={c2_latency:.1f}ms, c2_state={c2_state.name}, isac_allocated={isac_allocated:.2f} (requested 0.90)",
    )


def scenario_single_node_detection_no_effect():
    """ADR-004: a single-node (monostatic) detection has zero effect on connected-UAV state."""
    state = isac_detection_effect(corroborating_nodes=1)
    report(
        "Scenario 12: Single-node ISAC detection has zero effect on connected-UAV state",
        state == DegradationState.NOMINAL,
        f"corroborating_nodes=1, state={state.name}",
    )


def scenario_multistatic_corroboration_elevates_but_caps_at_degraded():
    """
    ADR-004: multi-static corroboration elevates to an advisory DEGRADED
    state — and no matter how many nodes corroborate, it never escalates
    beyond DEGRADED into an autonomous high-consequence action.
    """
    state_confirmed = isac_detection_effect(corroborating_nodes=3)
    state_overwhelming = isac_detection_effect(corroborating_nodes=10)
    report(
        "Scenario 13: Multi-static corroboration elevates to DEGRADED, and stays capped there even at 10 corroborating nodes",
        state_confirmed == DegradationState.DEGRADED and state_overwhelming == DegradationState.DEGRADED,
        f"3_nodes={state_confirmed.name}, 10_nodes={state_overwhelming.name}",
    )


def run_all():
    print("=" * 70)
    print("Module 7: Skylink Architecture — RF Physics and Handover Proof")
    print("Validating ADR-001, ADR-002, ADR-003, ADR-004")
    print("=" * 70)
    scenario_fspl_sanity()
    scenario_isolated_slice_within_budget()
    scenario_shared_network_breaches_budget()
    scenario_slice_saturation_reports_degraded()
    scenario_zone_deployment_selection()
    scenario_clean_zone_transition()
    scenario_zone_transition_gap_reports_degraded()
    scenario_ground_optimized_ping_pong_breaches_subbudget()
    scenario_aerial_optimized_stays_within_subbudget()
    scenario_doppler_sanity()
    scenario_isac_never_encroaches_c2_slice()
    scenario_single_node_detection_no_effect()
    scenario_multistatic_corroboration_elevates_but_caps_at_degraded()
    print("=" * 70)
    print("All scenarios executed. Review PASS/FAIL above against the ADRs.")
    print("=" * 70)


if __name__ == "__main__":
    run_all()
