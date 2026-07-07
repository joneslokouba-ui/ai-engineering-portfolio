"""
failsafe_sim.py

Module 5: Sentinel Architecture — Discrete-Event Fail-Safe Proof

This is NOT a flight physics simulator. It is a discrete-event proof that the
architecture decisions in ADR-001 (fail-safe boundary), ADR-002 (latency budget),
and ADR-003 (degradation ladder) hold under adversarial and degraded conditions.

Each scenario below asserts a specific claim made in an ADR. If any assertion
fails, the corresponding architectural decision is not actually being honored
by the design — which is the point of writing this as a proof, not a demo.

Run:
    python failsafe_sim.py
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
import random


# ---------------------------------------------------------------------------
# ADR-003: Fixed degradation ladder. Layers may only report one of these four
# states — no ad hoc states are permitted, by design.
# ---------------------------------------------------------------------------
class DegradationState(Enum):
    NOMINAL = 0
    DEGRADED = 1
    LOST = 2
    FAIL_SAFE = 3


def worst_of(states: list[DegradationState]) -> DegradationState:
    """ADR-003: aggregation is always worst-of, never average or majority."""
    return max(states, key=lambda s: s.value)


# ---------------------------------------------------------------------------
# ADR-001: Control layer only accepts a fixed, whitelisted set of intents.
# Nothing outside this set can ever reach the actuators, regardless of what
# the Decision layer sends.
# ---------------------------------------------------------------------------
class IntentType(Enum):
    HOVER = "HOVER"
    LOITER = "LOITER"
    GOTO = "GOTO"
    RETURN_TO_HOME = "RETURN_TO_HOME"
    LAND = "LAND"


WHITELISTED_INTENTS = {
    IntentType.HOVER,
    IntentType.LOITER,
    IntentType.GOTO,
    IntentType.RETURN_TO_HOME,
    IntentType.LAND,
}

# Safety envelope limits referenced in ADR-001 (illustrative values).
MAX_VELOCITY_MPS = 12.0
MAX_TILT_DEG = 35.0


@dataclass
class Intent:
    kind: IntentType | str          # deliberately allow "str" so we can inject garbage
    velocity_mps: float = 0.0
    tilt_deg: float = 0.0
    payload: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# ADR-002: per-layer latency budgets (illustrative, ms). A layer that exceeds
# its budget must fail fast (STALE / DEGRADE) rather than emit a late result.
# ---------------------------------------------------------------------------
PERCEPTION_BUDGET_MS = 50
DECISION_BUDGET_MS = 60


@dataclass
class PerceptionOutput:
    state: DegradationState
    confidence: float
    latency_ms: float


class PerceptionLayer:
    """Simulates sensor fusion + edge inference with configurable failure modes."""

    def process(self, latency_ms: float, confidence: float) -> PerceptionOutput:
        if latency_ms > PERCEPTION_BUDGET_MS:
            # ADR-002: fail fast rather than forward a late frame.
            return PerceptionOutput(DegradationState.LOST, confidence=0.0, latency_ms=latency_ms)
        if confidence < 0.5:
            return PerceptionOutput(DegradationState.DEGRADED, confidence=confidence, latency_ms=latency_ms)
        return PerceptionOutput(DegradationState.NOMINAL, confidence=confidence, latency_ms=latency_ms)


class DecisionLayer:
    """
    Simulates the planning layer. Deliberately allows injection of malformed
    or adversarial intents to prove the Control layer (not this layer) is
    what actually enforces safety — per ADR-001, the Decision layer is NOT
    trusted, only checked.
    """

    def decide(
        self,
        perception: PerceptionOutput,
        comms_state: DegradationState,
        latency_ms: float,
        forced_intent: Intent | None = None,
    ) -> tuple[DegradationState, Intent]:
        # ADR-002: Decision layer also fails fast on its own budget.
        if latency_ms > DECISION_BUDGET_MS:
            return DegradationState.LOST, Intent(IntentType.LOITER)

        # ADR-003: worst-of aggregation across all inputs this layer depends on.
        inputs = [perception.state, comms_state]
        overall_state = worst_of(inputs)

        # ADR-004: compound-failure escalation. Worst-of alone treats "one
        # input LOST" and "every input LOST simultaneously" identically. If
        # two or more independent inputs are LOST at the same time, the
        # aircraft has neither reliable sensing nor a reliable comms channel,
        # and continued navigation (RETURN_TO_HOME) is no longer a safe
        # option. Escalate to FAIL_SAFE, which maps to LAND. This is
        # deliberately narrow: a single LOST input does not trigger this.
        lost_count = sum(1 for s in inputs if s == DegradationState.LOST)
        if lost_count >= 2:
            overall_state = DegradationState.FAIL_SAFE

        # If a test wants to inject an adversarial/malformed intent regardless
        # of state, allow it — this is exactly the case ADR-001 must survive.
        if forced_intent is not None:
            return overall_state, forced_intent

        if overall_state == DegradationState.NOMINAL:
            return overall_state, Intent(IntentType.GOTO, velocity_mps=8.0, tilt_deg=15.0)
        elif overall_state == DegradationState.DEGRADED:
            return overall_state, Intent(IntentType.LOITER, velocity_mps=2.0, tilt_deg=5.0)
        elif overall_state == DegradationState.LOST:
            return overall_state, Intent(IntentType.RETURN_TO_HOME, velocity_mps=4.0, tilt_deg=10.0)
        else:  # FAIL_SAFE
            return overall_state, Intent(IntentType.LAND, velocity_mps=1.0, tilt_deg=0.0)


class ControlLayer:
    """
    The trusted boundary. ADR-001: this layer has no dependency on any ML
    model or non-deterministic code path, and independently validates every
    intent against the whitelist and the safety envelope before execution.
    """

    def __init__(self):
        self.executed_log: list[Intent] = []
        self.rejected_log: list[Intent] = []

    def execute(self, intent: Intent) -> Intent:
        if not self._is_valid(intent):
            self.rejected_log.append(intent)
            # ADR-001: on rejection, fall back to the single most conservative
            # pre-verified maneuver — never pass the bad intent through.
            fallback = Intent(IntentType.LOITER, velocity_mps=0.0, tilt_deg=0.0)
            self.executed_log.append(fallback)
            return fallback

        self.executed_log.append(intent)
        return intent

    def _is_valid(self, intent: Intent) -> bool:
        if intent.kind not in WHITELISTED_INTENTS:
            return False
        if intent.velocity_mps < 0 or intent.velocity_mps > MAX_VELOCITY_MPS:
            return False
        if intent.tilt_deg < 0 or intent.tilt_deg > MAX_TILT_DEG:
            return False
        return True


# ---------------------------------------------------------------------------
# Scenario harness
# ---------------------------------------------------------------------------
def report(name: str, passed: bool, detail: str = "") -> None:
    status = "PASS" if passed else "FAIL"
    line = f"[{status}] {name}"
    if detail:
        line += f" — {detail}"
    print(line)


def scenario_nominal():
    """Baseline: healthy inputs should produce a GOTO intent, executed as-is."""
    perception = PerceptionLayer().process(latency_ms=30, confidence=0.9)
    state, intent = DecisionLayer().decide(perception, DegradationState.NOMINAL, latency_ms=20)
    executed = ControlLayer().execute(intent)
    report(
        "Scenario 1: Nominal operation produces GOTO",
        state == DegradationState.NOMINAL and executed.kind == IntentType.GOTO,
        f"state={state.name}, executed={executed.kind}",
    )


def scenario_perception_timeout():
    """ADR-002: a perception layer exceeding its budget must emit LOST, not late data."""
    perception = PerceptionLayer().process(latency_ms=90, confidence=0.95)  # over 50ms budget
    state, intent = DecisionLayer().decide(perception, DegradationState.NOMINAL, latency_ms=20)
    executed = ControlLayer().execute(intent)
    report(
        "Scenario 2: Perception timeout triggers LOST -> RETURN_TO_HOME",
        perception.state == DegradationState.LOST and executed.kind == IntentType.RETURN_TO_HOME,
        f"perception_state={perception.state.name}, executed={executed.kind}",
    )


def scenario_low_confidence_degrades():
    """Low-confidence perception (not timed out) should degrade, not fail outright."""
    perception = PerceptionLayer().process(latency_ms=30, confidence=0.3)
    state, intent = DecisionLayer().decide(perception, DegradationState.NOMINAL, latency_ms=20)
    executed = ControlLayer().execute(intent)
    report(
        "Scenario 3: Low confidence produces DEGRADED -> LOITER",
        state == DegradationState.DEGRADED and executed.kind == IntentType.LOITER,
        f"state={state.name}, executed={executed.kind}",
    )


def scenario_comms_and_sensor_worst_of():
    """ADR-003: worst-of aggregation. Comms LOST + perception NOMINAL must still yield LOST."""
    perception = PerceptionLayer().process(latency_ms=30, confidence=0.95)  # NOMINAL
    state, intent = DecisionLayer().decide(perception, DegradationState.LOST, latency_ms=20)
    executed = ControlLayer().execute(intent)
    report(
        "Scenario 4: Worst-of aggregation (comms LOST overrides healthy perception)",
        state == DegradationState.LOST and executed.kind == IntentType.RETURN_TO_HOME,
        f"aggregated_state={state.name}, executed={executed.kind}",
    )


def scenario_adversarial_intent_rejected():
    """
    ADR-001, the core claim: even if the Decision layer sends a completely
    malformed or out-of-envelope intent (bug, spoofed input, adversarial
    attack), the Control layer must reject it and fall back safely — it must
    NEVER execute it as-is.
    """
    perception = PerceptionLayer().process(latency_ms=20, confidence=0.9)
    garbage_intent = Intent(kind="FULL_THROTTLE_DIVE", velocity_mps=999.0, tilt_deg=89.0)
    state, intent = DecisionLayer().decide(
        perception, DegradationState.NOMINAL, latency_ms=20, forced_intent=garbage_intent
    )
    control = ControlLayer()
    executed = control.execute(intent)
    report(
        "Scenario 5: Adversarial/malformed intent is rejected, never executed",
        executed.kind == IntentType.LOITER
        and executed.velocity_mps == 0.0
        and len(control.rejected_log) == 1
        and control.rejected_log[0] is garbage_intent,
        f"rejected={control.rejected_log[0].kind}, fallback_executed={executed.kind}",
    )


def scenario_out_of_envelope_whitelisted_intent_rejected():
    """
    A more subtle case: the intent TYPE is whitelisted (GOTO), but its
    velocity exceeds the safety envelope. ADR-001 requires the Control layer
    to validate envelope limits independently, not just the intent type.
    """
    perception = PerceptionLayer().process(latency_ms=20, confidence=0.9)
    over_limit_intent = Intent(kind=IntentType.GOTO, velocity_mps=50.0, tilt_deg=15.0)  # > 12 m/s max
    state, intent = DecisionLayer().decide(
        perception, DegradationState.NOMINAL, latency_ms=20, forced_intent=over_limit_intent
    )
    control = ControlLayer()
    executed = control.execute(intent)
    report(
        "Scenario 6: Whitelisted intent type but out-of-envelope value is rejected",
        executed.kind == IntentType.LOITER and len(control.rejected_log) == 1,
        f"requested_velocity={over_limit_intent.velocity_mps}m/s (max={MAX_VELOCITY_MPS}), "
        f"fallback_executed={executed.kind}",
    )


def scenario_total_failure_fail_safe():
    """
    ADR-004: Comms LOST + perception LOST simultaneously must escalate to
    FAIL_SAFE and produce LAND, not RETURN_TO_HOME. This is the fix for the
    gap originally exposed by this same scenario (see ADR-004 for history):
    worst-of aggregation alone could not distinguish "one thing failed" from
    "everything failed at once."
    """
    perception = PerceptionOutput(DegradationState.LOST, confidence=0.0, latency_ms=999)
    state, intent = DecisionLayer().decide(perception, DegradationState.LOST, latency_ms=20)
    executed = ControlLayer().execute(intent)
    report(
        "Scenario 7: Simultaneous comms + perception loss escalates to FAIL_SAFE -> LAND",
        state == DegradationState.FAIL_SAFE and executed.kind == IntentType.LAND,
        f"state={state.name}, executed={executed.kind}",
    )


def scenario_single_lost_does_not_escalate():
    """
    ADR-004 negative case: the escalation rule must be narrow. A single LOST
    input (perception LOST, comms healthy) must NOT escalate to FAIL_SAFE —
    it should still resolve to plain LOST -> RETURN_TO_HOME, exactly as
    before ADR-004. This proves the fix targets compound failure specifically
    and does not make the system over-conservative on ordinary single-point
    failures.
    """
    perception = PerceptionOutput(DegradationState.LOST, confidence=0.0, latency_ms=999)
    state, intent = DecisionLayer().decide(perception, DegradationState.NOMINAL, latency_ms=20)
    executed = ControlLayer().execute(intent)
    report(
        "Scenario 8: Single LOST input does not over-escalate (stays LOST -> RETURN_TO_HOME)",
        state == DegradationState.LOST and executed.kind == IntentType.RETURN_TO_HOME,
        f"state={state.name}, executed={executed.kind}",
    )


def run_all():
    random.seed(42)
    print("=" * 70)
    print("Module 5: Sentinel Architecture — Fail-Safe Boundary Proof")
    print("Validating ADR-001, ADR-002, ADR-003, ADR-004")
    print("=" * 70)
    scenario_nominal()
    scenario_perception_timeout()
    scenario_low_confidence_degrades()
    scenario_comms_and_sensor_worst_of()
    scenario_adversarial_intent_rejected()
    scenario_out_of_envelope_whitelisted_intent_rejected()
    scenario_total_failure_fail_safe()
    scenario_single_lost_does_not_escalate()
    print("=" * 70)
    print("All scenarios executed. Review PASS/FAIL above against the ADRs.")
    print("=" * 70)


if __name__ == "__main__":
    run_all()