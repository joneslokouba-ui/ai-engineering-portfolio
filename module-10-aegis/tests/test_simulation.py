"""
AEGIS — Simulation & Governance Tests
Module 10, ai-engineering-portfolio
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from src.simulation.discrete_event_engine import run_scenario
from src.governance.authority_boundary import (
    AuthorityBoundary,
    AdjudicationRecord,
    AuthorityBoundaryViolation,
)


class TestDiscreteEventEngine:
    @pytest.mark.parametrize("seed", [1, 2, 3])
    def test_full_detection_rate(self, seed):
        """Acceptance test: every injected typology case must be
        detected and escalated. This is the module's core promise."""
        result, _ = run_scenario(seed)
        assert result.detection_rate == 1.0, (
            f"Seed {seed}: only {result.n_cases_detected}/{result.n_cases_injected} "
            f"cases detected. Undetected: {result.undetected_cases}"
        )

    def test_false_escalation_rate_is_realistic(self):
        """A 0% false-escalation rate would be as suspicious as a 100%
        one -- it would suggest the escalation threshold is trivially
        separating classes rather than doing real risk-based triage."""
        result, _ = run_scenario(seed=42)
        false_rate = result.n_false_escalations / max(result.n_escalations, 1)
        assert 0.0 < false_rate < 0.3, (
            f"False-escalation rate {false_rate:.1%} outside the expected "
            "realistic band -- investigate before trusting this result."
        )

    def test_scenario_result_is_reproducible(self):
        """Same seed must produce identical results -- required for the
        module's detection-rate claims to be verifiable/auditable."""
        result_a, _ = run_scenario(seed=7)
        result_b, _ = run_scenario(seed=7)
        assert result_a.n_transactions == result_b.n_transactions
        assert result_a.detection_rate == result_b.detection_rate
        assert result_a.n_escalations == result_b.n_escalations


class TestAuthorityBoundary:
    def test_tier_0_2_actions_are_autonomous(self):
        boundary = AuthorityBoundary()
        case = boundary.escalate("0xabc", 0.9, "CRITICAL", {})
        assert case.status == "pending_review"
        assert case in boundary.pending_cases()

    def test_tier_3_blocked_without_adjudication(self):
        boundary = AuthorityBoundary()
        case = boundary.escalate("0xabc", 0.9, "CRITICAL", {})
        with pytest.raises(AuthorityBoundaryViolation):
            boundary.request_enforcement(case.case_id, "freeze_wallet")

    def test_tier_3_authorized_after_confirmed_adjudication(self):
        boundary = AuthorityBoundary()
        case = boundary.escalate("0xabc", 0.9, "CRITICAL", {})
        boundary.record_adjudication(
            AdjudicationRecord(case.case_id, "analyst_1", "confirmed", "Confirmed match.")
        )
        result = boundary.request_enforcement(case.case_id, "freeze_wallet")
        assert result["action"] == "freeze_wallet"
        assert result["authorized_by"] == "analyst_1"
        assert len(boundary.enforcement_log()) == 1

    def test_cleared_case_cannot_trigger_enforcement(self):
        """A 'cleared' adjudication must NOT authorize enforcement --
        only 'confirmed' does. This is the distinction that prevents a
        false-positive review from accidentally unlocking Tier 3."""
        boundary = AuthorityBoundary()
        case = boundary.escalate("0xabc", 0.4, "MEDIUM", {})
        boundary.record_adjudication(
            AdjudicationRecord(case.case_id, "analyst_1", "cleared", "False positive.")
        )
        with pytest.raises(AuthorityBoundaryViolation):
            boundary.request_enforcement(case.case_id, "freeze_wallet")

    def test_no_bypass_parameter_exists(self):
        """Defensive test: request_enforcement's signature must not
        grow a bypass/force/override parameter over time."""
        import inspect
        sig = inspect.signature(AuthorityBoundary.request_enforcement)
        param_names = set(sig.parameters.keys())
        forbidden = {"force", "override", "bypass", "skip_adjudication", "auto_approve"}
        assert not (param_names & forbidden), (
            f"request_enforcement gained a bypass-like parameter: {param_names & forbidden}"
        )

    def test_unknown_case_id_raises_on_adjudication(self):
        boundary = AuthorityBoundary()
        with pytest.raises(ValueError):
            boundary.record_adjudication(
                AdjudicationRecord("nonexistent-case", "analyst_1", "confirmed", "n/a")
            )