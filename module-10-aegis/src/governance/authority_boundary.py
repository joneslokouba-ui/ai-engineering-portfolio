"""
AEGIS — Authority Boundary (Governance)
Module 10, ai-engineering-portfolio

Enforces the zero-autonomous-tier boundary defined in ADR-010, mirroring
Module 8 (Vigil): AEGIS is a decision-support system, not a decision-
making system. This module is the single choke point through which
every action the pipeline might take is routed -- scoring and queueing
are permitted autonomously; freezing funds, filing a SAR, or notifying
a regulator are hard-blocked without a recorded human adjudication.

This is deliberately NOT a soft convention (e.g. "just don't call the
freeze function"). It's an enforced boundary: Tier 3 actions raise
AuthorityBoundaryViolation if attempted without a matching, valid
AdjudicationRecord. There is no bypass parameter, no "auto-approve"
flag, and no override -- by design.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum


class ActionTier(IntEnum):
    INGEST_AND_SCORE = 0
    FLAG_FOR_REVIEW = 1
    POPULATE_ESCALATION_QUEUE = 2
    ENFORCEMENT_ACTION = 3  # freeze wallet / file SAR / notify regulator


AUTONOMOUS_TIERS = {ActionTier.INGEST_AND_SCORE, ActionTier.FLAG_FOR_REVIEW, ActionTier.POPULATE_ESCALATION_QUEUE}


class AuthorityBoundaryViolation(RuntimeError):
    """Raised whenever a Tier 3 action is attempted without a valid,
    matching human adjudication record. This exception is not meant to
    be caught and suppressed anywhere in the pipeline -- it is a hard
    stop signaling a design/integration error, not an expected control
    flow branch."""


@dataclass
class AdjudicationRecord:
    """
    Represents a human reviewer's decision on an escalated case. This is
    the ONLY artifact that can authorize a Tier 3 action. In a real
    deployment this would be persisted (audit database, case
    management system) with reviewer identity, timestamp, and
    justification -- fields are included here to make that contract
    explicit even in the portfolio version.
    """

    case_id: str
    reviewer_id: str
    decision: str  # "confirmed" | "cleared"
    justification: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def authorizes_enforcement(self) -> bool:
        return self.decision == "confirmed"


@dataclass
class EscalationCase:
    case_id: str
    wallet: str
    composite_score: float
    risk_tier: str
    evidence: dict
    status: str = "pending_review"  # pending_review | cleared | confirmed


class AuthorityBoundary:
    """
    Central gatekeeper. All escalation and enforcement actions in the
    pipeline must pass through this object -- it is intentionally the
    only class in the codebase permitted to hold enforcement logic.
    """

    def __init__(self):
        self._queue: dict[str, EscalationCase] = {}
        self._adjudications: dict[str, AdjudicationRecord] = {}
        self._enforcement_log: list[dict] = []

    # ---- Tier 0-2: fully autonomous -------------------------------
    def escalate(self, wallet: str, composite_score: float, risk_tier: str, evidence: dict) -> EscalationCase:
        """Tier 2 action: populate the escalation queue. Always permitted
        autonomously -- this creates a case for human review, it does not
        act on the wallet in any way."""
        case_id = f"case-{wallet}-{len(self._queue)}"
        case = EscalationCase(case_id, wallet, composite_score, risk_tier, evidence)
        self._queue[case_id] = case
        return case

    def pending_cases(self) -> list[EscalationCase]:
        return [c for c in self._queue.values() if c.status == "pending_review"]

    # ---- Human adjudication (required before Tier 3) ---------------
    def record_adjudication(self, record: AdjudicationRecord) -> None:
        if record.case_id not in self._queue:
            raise ValueError(f"Unknown case_id: {record.case_id}")
        self._adjudications[record.case_id] = record
        self._queue[record.case_id].status = record.decision

    # ---- Tier 3: enforcement, hard-gated ----------------------------
    def request_enforcement(self, case_id: str, action: str) -> dict:
        """
        The ONLY path by which an enforcement action (freeze wallet,
        file SAR, notify regulator) can be logged. Raises
        AuthorityBoundaryViolation if no valid confirming adjudication
        exists for this case -- there is no autonomous path to this
        method's success branch.
        """
        record = self._adjudications.get(case_id)
        if record is None or not record.authorizes_enforcement():
            raise AuthorityBoundaryViolation(
                f"Tier 3 action '{action}' blocked for case {case_id}: "
                f"no confirming human adjudication on file. "
                f"AEGIS cannot authorize enforcement actions autonomously."
            )

        entry = {
            "case_id": case_id,
            "action": action,
            "authorized_by": record.reviewer_id,
            "justification": record.justification,
            "timestamp": datetime.now(timezone.utc),
        }
        self._enforcement_log.append(entry)
        return entry

    def enforcement_log(self) -> list[dict]:
        return list(self._enforcement_log)


if __name__ == "__main__":
    boundary = AuthorityBoundary()

    # Tier 0-2: fully autonomous, always succeeds
    case = boundary.escalate(
        wallet="0xdeadbeef1234",
        composite_score=0.91,
        risk_tier="CRITICAL",
        evidence={"sanctions_rule_score": 1.0, "ml_score": 0.85},
    )
    print(f"Escalated case: {case.case_id} (status={case.status})")

    # Attempt Tier 3 WITHOUT adjudication -- must be blocked
    try:
        boundary.request_enforcement(case.case_id, "freeze_wallet")
        print("ERROR: enforcement should have been blocked!")
    except AuthorityBoundaryViolation as e:
        print(f"Correctly blocked: {e}")

    # Human reviewer adjudicates
    boundary.record_adjudication(
        AdjudicationRecord(
            case_id=case.case_id,
            reviewer_id="analyst_jsh",
            decision="confirmed",
            justification="Direct OFAC SDN match confirmed via manual lookup.",
        )
    )

    # Now Tier 3 is authorized
    result = boundary.request_enforcement(case.case_id, "freeze_wallet")
    print(f"Enforcement authorized: {result}")

    # Verify a case adjudicated as 'cleared' still cannot trigger enforcement
    case2 = boundary.escalate("0xfeedface5678", 0.4, "MEDIUM", {})
    boundary.record_adjudication(
        AdjudicationRecord(case2.case_id, "analyst_jsh", "cleared", "False positive -- known exchange hot wallet.")
    )
    try:
        boundary.request_enforcement(case2.case_id, "freeze_wallet")
        print("ERROR: cleared case should not authorize enforcement!")
    except AuthorityBoundaryViolation as e:
        print(f"Correctly blocked (cleared case): {e}")