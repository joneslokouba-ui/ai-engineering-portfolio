"""
sentry_sim.py

Module 6: Sentry Architecture — Discrete-Event Fraud-Decision Proof

This is NOT a production fraud model. It is a discrete-event proof that the
architecture decisions in ADR-001 (authority boundary), ADR-002 (latency
budget), ADR-003 (fail-open/fail-closed policy), ADR-004 (asymmetric error
handling), ADR-005 (audit/explainability), and ADR-006 (forensic attribution
feedback) hold under adversarial and degraded conditions.

Each scenario below asserts a specific claim made in an ADR. If any assertion
fails, the corresponding architectural decision is not actually being honored
by the design.

Run:
    python sentry_sim.py
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


# ---------------------------------------------------------------------------
# ADR-001: Tier 1 actions the Decision layer may take autonomously. Tier 2
# actions may only ever be *recommended*, never auto-executed.
# ---------------------------------------------------------------------------
class Action(Enum):
    APPROVE = "APPROVE"
    DECLINE = "DECLINE"
    HOLD_FOR_REVIEW = "HOLD_FOR_REVIEW"
    ESCALATE_TIER2 = "ESCALATE_TIER2"  # routed to Human Escalation queue only


class Tier2Type(Enum):
    PERMANENT_SUSPENSION = "PERMANENT_SUSPENSION"
    FUND_FREEZE = "FUND_FREEZE"
    LAW_ENFORCEMENT_REFERRAL = "LAW_ENFORCEMENT_REFERRAL"


# ---------------------------------------------------------------------------
# ADR-002: per-layer latency budgets (ms). Exceeding a budget must produce a
# timeout signal, never a late/forced result.
# ---------------------------------------------------------------------------
INGESTION_BUDGET_MS = 150
SCORING_BUDGET_MS = 100
AUDIT_BUDGET_MS = 20

# ADR-003: fail-open exception bounds.
FAILOPEN_MAX_AMOUNT = 25.0

# ADR-004: independently configurable thresholds.
DEFAULT_DECLINE_THRESHOLD = 0.80
DEFAULT_FRICTION_THRESHOLD = 0.50


@dataclass
class TrustCacheEntry:
    trusted: bool
    fresh: bool  # False simulates a stale or missing cache entry


@dataclass
class IngestionResult:
    timed_out: bool
    latency_ms: float


@dataclass
class ScoringResult:
    timed_out: bool
    score: float
    latency_ms: float


# ADR-006: registry entries only affect a decision if human-confirmed and
# not expired. An unconfirmed or expired entry must have zero effect.
@dataclass
class RiskRegistryEntry:
    identifier: str
    confirmed: bool   # False = candidate cluster, not yet human-reviewed
    expired: bool      # True = past its review cadence, requires re-confirmation
    risk_weight: float # additive weight applied to the fraud score, never a verdict on its own


@dataclass
class DecisionRecord:
    """What ADR-005 requires to be captured for every decision."""
    action: Action
    score: float | None
    decline_threshold: float
    friction_threshold: float
    reason: str
    tier2_type: Tier2Type | None = None
    registry_weight_applied: float = 0.0  # ADR-006: 0.0 unless a confirmed, non-expired entry matched


class IngestionLayer:
    def extract(self, latency_ms: float) -> IngestionResult:
        return IngestionResult(timed_out=latency_ms > INGESTION_BUDGET_MS, latency_ms=latency_ms)


class ScoringLayer:
    def score_transaction(self, latency_ms: float, score: float) -> ScoringResult:
        return ScoringResult(timed_out=latency_ms > SCORING_BUDGET_MS, score=score, latency_ms=latency_ms)


class AuditLayer:
    """
    ADR-005: audit writes are synchronous and must be confirmed within a
    tight budget. A write that fails or times out is NOT silently ignored —
    the caller (Decision layer) must treat it as a scoring-equivalent
    failure and fail closed.
    """

    def __init__(self):
        self.records: list[DecisionRecord] = []

    def write(self, record: DecisionRecord, latency_ms: float, force_fail: bool = False) -> bool:
        if force_fail or latency_ms > AUDIT_BUDGET_MS:
            return False  # not confirmed — caller must not treat this decision as final
        self.records.append(record)
        return True


class HumanEscalationLayer:
    """Tier 2 recommendations land here. Nothing in this layer auto-executes."""

    def __init__(self):
        self.queue: list[Tier2Type] = []

    def enqueue(self, tier2_type: Tier2Type) -> None:
        self.queue.append(tier2_type)


class DecisionLayer:
    def __init__(
        self,
        decline_threshold: float = DEFAULT_DECLINE_THRESHOLD,
        friction_threshold: float = DEFAULT_FRICTION_THRESHOLD,
    ):
        self.decline_threshold = decline_threshold
        self.friction_threshold = friction_threshold

    def decide(
        self,
        ingestion: IngestionResult,
        scoring: ScoringResult,
        amount: float,
        trust: TrustCacheEntry,
        audit: AuditLayer,
        escalation: HumanEscalationLayer,
        audit_latency_ms: float = 5.0,
        audit_force_fail: bool = False,
        forced_tier2_request: Tier2Type | None = None,
        registry_entry: RiskRegistryEntry | None = None,
    ) -> DecisionRecord:
        # ADR-001: an adversarial or buggy request for a Tier 2 action is
        # NEVER auto-executed, regardless of score or timing. It is only
        # ever queued for human review.
        if forced_tier2_request is not None:
            escalation.enqueue(forced_tier2_request)
            record = DecisionRecord(
                action=Action.ESCALATE_TIER2,
                score=scoring.score if not scoring.timed_out else None,
                decline_threshold=self.decline_threshold,
                friction_threshold=self.friction_threshold,
                reason="Tier 2 action requested — routed to human escalation, not auto-executed",
                tier2_type=forced_tier2_request,
            )
            self._finalize(record, audit, audit_latency_ms, audit_force_fail)
            return record

        # ADR-002/ADR-003: ingestion or scoring timeout triggers the
        # fail-closed default, with a narrow, bounded fail-open exception.
        if ingestion.timed_out or scoring.timed_out:
            if amount < FAILOPEN_MAX_AMOUNT and trust.trusted and trust.fresh:
                record = DecisionRecord(
                    action=Action.APPROVE,
                    score=None,
                    decline_threshold=self.decline_threshold,
                    friction_threshold=self.friction_threshold,
                    reason="Timeout, but bounded fail-open exception applies (low amount, trusted, fresh cache)",
                )
            else:
                record = DecisionRecord(
                    action=Action.HOLD_FOR_REVIEW,
                    score=None,
                    decline_threshold=self.decline_threshold,
                    friction_threshold=self.friction_threshold,
                    reason="Timeout, fail-closed default (exception conditions not met)",
                )
            self._finalize(record, audit, audit_latency_ms, audit_force_fail)
            return record

        # ADR-004: two independently configurable thresholds, not one
        # global accuracy-optimized cutoff.
        # ADR-006: a confirmed, non-expired registry match adds a risk weight
        # to the score BEFORE thresholding — it flows through the same
        # governed mechanism as everything else. An unconfirmed or expired
        # entry contributes nothing; this is checked explicitly, not assumed.
        base_score = scoring.score
        weight_applied = 0.0
        if registry_entry is not None and registry_entry.confirmed and not registry_entry.expired:
            weight_applied = registry_entry.risk_weight
        effective_score = min(1.0, base_score + weight_applied)

        if effective_score >= self.decline_threshold:
            action = Action.DECLINE
            reason = f"Effective score {effective_score:.2f} >= decline threshold {self.decline_threshold:.2f}"
        elif effective_score >= self.friction_threshold:
            action = Action.HOLD_FOR_REVIEW
            reason = (
                f"Effective score {effective_score:.2f} in friction band "
                f"[{self.friction_threshold:.2f}, {self.decline_threshold:.2f})"
            )
        else:
            action = Action.APPROVE
            reason = f"Effective score {effective_score:.2f} below friction threshold {self.friction_threshold:.2f}"

        if weight_applied > 0:
            reason += f" (base score {base_score:.2f} + registry weight {weight_applied:.2f})"

        # ADR-006's core boundary: no matter how large the registry weight,
        # it can only push the outcome within the Tier 1 action set already
        # governed by ADR-004's thresholds. It can NEVER itself produce a
        # Tier 2 escalation — that still requires the explicit, separately
        # authorized forced_tier2_request path above, which registry lookups
        # never call into.
        record = DecisionRecord(
            action=action,
            score=base_score,
            decline_threshold=self.decline_threshold,
            friction_threshold=self.friction_threshold,
            reason=reason,
            registry_weight_applied=weight_applied,
        )
        self._finalize(record, audit, audit_latency_ms, audit_force_fail)
        return record

    def _finalize(
        self,
        record: DecisionRecord,
        audit: AuditLayer,
        audit_latency_ms: float,
        audit_force_fail: bool,
    ) -> None:
        """
        ADR-005: a decision is not final until its audit record is
        confirmed. If the audit write fails, downgrade to the fail-closed
        action — the original (possibly more permissive) action must not
        stand without a corresponding record.
        """
        confirmed = audit.write(record, latency_ms=audit_latency_ms, force_fail=audit_force_fail)
        if not confirmed and record.action != Action.HOLD_FOR_REVIEW:
            record.action = Action.HOLD_FOR_REVIEW
            record.reason = "Audit write not confirmed — original action downgraded to fail-closed (ADR-005)"
            # Retry the audit write for the downgraded record itself so the
            # fallback decision is still captured once the sink recovers.
            audit.write(record, latency_ms=audit_latency_ms, force_fail=False)


# ---------------------------------------------------------------------------
# Scenario harness
# ---------------------------------------------------------------------------
def report(name: str, passed: bool, detail: str = "") -> None:
    status = "PASS" if passed else "FAIL"
    line = f"[{status}] {name}"
    if detail:
        line += f" — {detail}"
    print(line)


def scenario_nominal_approve():
    """Low score, healthy pipeline -> APPROVE, audit confirmed."""
    ingestion = IngestionLayer().extract(latency_ms=40)
    scoring = ScoringLayer().score_transaction(latency_ms=60, score=0.10)
    audit, escalation = AuditLayer(), HumanEscalationLayer()
    record = DecisionLayer().decide(ingestion, scoring, amount=80.0, trust=TrustCacheEntry(True, True),
                                     audit=audit, escalation=escalation)
    report("Scenario 1: Nominal low score -> APPROVE",
           record.action == Action.APPROVE and len(audit.records) == 1,
           f"action={record.action.value}")


def scenario_nominal_decline():
    """High score, healthy pipeline -> DECLINE."""
    ingestion = IngestionLayer().extract(latency_ms=40)
    scoring = ScoringLayer().score_transaction(latency_ms=60, score=0.95)
    audit, escalation = AuditLayer(), HumanEscalationLayer()
    record = DecisionLayer().decide(ingestion, scoring, amount=500.0, trust=TrustCacheEntry(False, False),
                                     audit=audit, escalation=escalation)
    report("Scenario 2: High score -> DECLINE",
           record.action == Action.DECLINE,
           f"action={record.action.value}")


def scenario_friction_band():
    """ADR-004: mid-range score lands in the friction band, not a flat decline."""
    ingestion = IngestionLayer().extract(latency_ms=40)
    scoring = ScoringLayer().score_transaction(latency_ms=60, score=0.65)
    audit, escalation = AuditLayer(), HumanEscalationLayer()
    record = DecisionLayer().decide(ingestion, scoring, amount=200.0, trust=TrustCacheEntry(False, False),
                                     audit=audit, escalation=escalation)
    report("Scenario 3: Mid-range score -> HOLD_FOR_REVIEW (friction band)",
           record.action == Action.HOLD_FOR_REVIEW,
           f"action={record.action.value}")


def scenario_timeout_failclosed_default():
    """ADR-003: timeout with high amount / untrusted account -> fail-closed default."""
    ingestion = IngestionLayer().extract(latency_ms=200)  # over budget
    scoring = ScoringLayer().score_transaction(latency_ms=0, score=0.0)
    audit, escalation = AuditLayer(), HumanEscalationLayer()
    record = DecisionLayer().decide(ingestion, scoring, amount=400.0, trust=TrustCacheEntry(False, False),
                                     audit=audit, escalation=escalation)
    report("Scenario 4: Timeout, high amount/untrusted -> HOLD_FOR_REVIEW (fail-closed default)",
           record.action == Action.HOLD_FOR_REVIEW,
           f"action={record.action.value}, reason={record.reason}")


def scenario_timeout_failopen_exception():
    """ADR-003: timeout, low amount + trusted + fresh cache -> bounded fail-open exception."""
    ingestion = IngestionLayer().extract(latency_ms=200)
    scoring = ScoringLayer().score_transaction(latency_ms=0, score=0.0)
    audit, escalation = AuditLayer(), HumanEscalationLayer()
    record = DecisionLayer().decide(ingestion, scoring, amount=10.0, trust=TrustCacheEntry(True, True),
                                     audit=audit, escalation=escalation)
    report("Scenario 5: Timeout, low amount/trusted/fresh -> APPROVE (fail-open exception)",
           record.action == Action.APPROVE,
           f"action={record.action.value}, reason={record.reason}")


def scenario_timeout_boundary_enforced():
    """ADR-003: same trust profile, amount just above the exception threshold -> must fail closed."""
    ingestion = IngestionLayer().extract(latency_ms=200)
    scoring = ScoringLayer().score_transaction(latency_ms=0, score=0.0)
    audit, escalation = AuditLayer(), HumanEscalationLayer()
    record = DecisionLayer().decide(ingestion, scoring, amount=25.01, trust=TrustCacheEntry(True, True),
                                     audit=audit, escalation=escalation)
    report("Scenario 6: Timeout, amount just above exception threshold -> HOLD_FOR_REVIEW",
           record.action == Action.HOLD_FOR_REVIEW,
           f"amount=25.01 (limit={FAILOPEN_MAX_AMOUNT}), action={record.action.value}")


def scenario_stale_cache_treated_as_untrusted():
    """ADR-003: a stale trust-cache entry must fail closed, never pass as an implicit trust."""
    ingestion = IngestionLayer().extract(latency_ms=200)
    scoring = ScoringLayer().score_transaction(latency_ms=0, score=0.0)
    audit, escalation = AuditLayer(), HumanEscalationLayer()
    record = DecisionLayer().decide(ingestion, scoring, amount=10.0, trust=TrustCacheEntry(True, fresh=False),
                                     audit=audit, escalation=escalation)
    report("Scenario 7: Timeout, stale trust cache -> HOLD_FOR_REVIEW (stale != trusted)",
           record.action == Action.HOLD_FOR_REVIEW,
           f"action={record.action.value}, reason={record.reason}")


def scenario_adversarial_tier2_rejected():
    """
    ADR-001, the core claim: a request (bug, spoofed input, adversarial
    manipulation) to directly execute a Tier 2 action must be routed to
    human escalation, never auto-executed — regardless of score.
    """
    ingestion = IngestionLayer().extract(latency_ms=40)
    scoring = ScoringLayer().score_transaction(latency_ms=60, score=0.99)
    audit, escalation = AuditLayer(), HumanEscalationLayer()
    record = DecisionLayer().decide(
        ingestion, scoring, amount=1000.0, trust=TrustCacheEntry(False, False),
        audit=audit, escalation=escalation,
        forced_tier2_request=Tier2Type.PERMANENT_SUSPENSION,
    )
    report("Scenario 8: Adversarial Tier 2 request routed to human escalation, never auto-executed",
           record.action == Action.ESCALATE_TIER2
           and len(escalation.queue) == 1
           and escalation.queue[0] == Tier2Type.PERMANENT_SUSPENSION,
           f"action={record.action.value}, queued={escalation.queue}")


def scenario_threshold_attribution():
    """ADR-004: changing thresholds changes outcomes, and the record captures which config was active."""
    ingestion = IngestionLayer().extract(latency_ms=40)
    scoring = ScoringLayer().score_transaction(latency_ms=60, score=0.55)
    audit, escalation = AuditLayer(), HumanEscalationLayer()

    default_decision = DecisionLayer().decide(ingestion, scoring, amount=100.0, trust=TrustCacheEntry(False, False),
                                               audit=audit, escalation=escalation)
    strict_decision = DecisionLayer(decline_threshold=0.50, friction_threshold=0.30).decide(
        ingestion, scoring, amount=100.0, trust=TrustCacheEntry(False, False), audit=audit, escalation=escalation
    )
    report(
        "Scenario 9: Threshold change alters outcome, and each record captures its own config",
        default_decision.action == Action.HOLD_FOR_REVIEW
        and strict_decision.action == Action.DECLINE
        and default_decision.decline_threshold == 0.80
        and strict_decision.decline_threshold == 0.50,
        f"default={default_decision.action.value}@{default_decision.decline_threshold}, "
        f"strict={strict_decision.action.value}@{strict_decision.decline_threshold}",
    )


def scenario_audit_failure_forces_failclosed():
    """
    ADR-005, the core claim: if the audit write cannot be confirmed, the
    decision is downgraded to the fail-closed action, even though the
    underlying score would otherwise have approved the transaction.
    """
    ingestion = IngestionLayer().extract(latency_ms=40)
    scoring = ScoringLayer().score_transaction(latency_ms=60, score=0.10)  # would otherwise APPROVE
    audit, escalation = AuditLayer(), HumanEscalationLayer()
    record = DecisionLayer().decide(
        ingestion, scoring, amount=80.0, trust=TrustCacheEntry(True, True),
        audit=audit, escalation=escalation,
        audit_force_fail=True,
    )
    report(
        "Scenario 10: Audit write failure downgrades an otherwise-APPROVE decision to HOLD_FOR_REVIEW",
        record.action == Action.HOLD_FOR_REVIEW and "Audit write not confirmed" in record.reason,
        f"action={record.action.value}, reason={record.reason}",
    )


def scenario_unconfirmed_cluster_no_effect():
    """
    ADR-006: an unconfirmed candidate cluster must have ZERO effect on the
    decision. A low base score stays APPROVE even with a large registry
    weight attached, because that weight was never human-confirmed.
    """
    ingestion = IngestionLayer().extract(latency_ms=40)
    scoring = ScoringLayer().score_transaction(latency_ms=60, score=0.10)
    audit, escalation = AuditLayer(), HumanEscalationLayer()
    unconfirmed_entry = RiskRegistryEntry(identifier="device-xyz", confirmed=False, expired=False, risk_weight=0.9)
    record = DecisionLayer().decide(
        ingestion, scoring, amount=80.0, trust=TrustCacheEntry(True, True),
        audit=audit, escalation=escalation, registry_entry=unconfirmed_entry,
    )
    report(
        "Scenario 11: Unconfirmed cluster has zero effect -> still APPROVE",
        record.action == Action.APPROVE and record.registry_weight_applied == 0.0,
        f"action={record.action.value}, weight_applied={record.registry_weight_applied}",
    )


def scenario_confirmed_registry_shifts_via_threshold():
    """
    ADR-006: a confirmed, non-expired registry match adds its weight to the
    score, and the RESULT flows through the same governed threshold system
    as any other transaction — it does not bypass it.
    """
    ingestion = IngestionLayer().extract(latency_ms=40)
    scoring = ScoringLayer().score_transaction(latency_ms=60, score=0.30)  # alone: APPROVE
    audit, escalation = AuditLayer(), HumanEscalationLayer()
    confirmed_entry = RiskRegistryEntry(identifier="device-xyz", confirmed=True, expired=False, risk_weight=0.35)
    record = DecisionLayer().decide(
        ingestion, scoring, amount=80.0, trust=TrustCacheEntry(True, True),
        audit=audit, escalation=escalation, registry_entry=confirmed_entry,
    )
    report(
        "Scenario 12: Confirmed registry match shifts 0.30 -> 0.65, into friction band via normal thresholds",
        record.action == Action.HOLD_FOR_REVIEW and record.registry_weight_applied == 0.35,
        f"action={record.action.value}, base_score={record.score}, weight_applied={record.registry_weight_applied}",
    )


def scenario_expired_registry_no_effect():
    """ADR-006: an expired entry (past its review cadence) must have zero effect, same as unconfirmed."""
    ingestion = IngestionLayer().extract(latency_ms=40)
    scoring = ScoringLayer().score_transaction(latency_ms=60, score=0.30)
    audit, escalation = AuditLayer(), HumanEscalationLayer()
    expired_entry = RiskRegistryEntry(identifier="device-xyz", confirmed=True, expired=True, risk_weight=0.35)
    record = DecisionLayer().decide(
        ingestion, scoring, amount=80.0, trust=TrustCacheEntry(True, True),
        audit=audit, escalation=escalation, registry_entry=expired_entry,
    )
    report(
        "Scenario 13: Expired registry entry has zero effect -> falls back to APPROVE",
        record.action == Action.APPROVE and record.registry_weight_applied == 0.0,
        f"action={record.action.value}, weight_applied={record.registry_weight_applied}",
    )


def scenario_registry_cannot_force_tier2():
    """
    ADR-006's core claim: even an extreme registry weight, engineered to
    look like an attempt to force a population-level suspension, can only
    ever move the outcome within the Tier 1 action set. It can NEVER itself
    produce a Tier 2 escalation — that path is only reachable through the
    separately authorized forced_tier2_request mechanism (ADR-001), which a
    registry match never triggers on its own.
    """
    ingestion = IngestionLayer().extract(latency_ms=40)
    scoring = ScoringLayer().score_transaction(latency_ms=60, score=0.50)
    audit, escalation = AuditLayer(), HumanEscalationLayer()
    extreme_entry = RiskRegistryEntry(identifier="device-xyz", confirmed=True, expired=False, risk_weight=5.0)
    record = DecisionLayer().decide(
        ingestion, scoring, amount=80.0, trust=TrustCacheEntry(True, True),
        audit=audit, escalation=escalation, registry_entry=extreme_entry,
    )
    report(
        "Scenario 14: Extreme registry weight still caps at DECLINE, never forces Tier 2 escalation",
        record.action == Action.DECLINE and record.tier2_type is None and len(escalation.queue) == 0,
        f"action={record.action.value}, tier2_type={record.tier2_type}, escalation_queue={escalation.queue}",
    )


def run_all():
    print("=" * 70)
    print("Module 6: Sentry Architecture — Fraud-Decision Boundary Proof")
    print("Validating ADR-001, ADR-002, ADR-003, ADR-004, ADR-005, ADR-006")
    print("=" * 70)
    scenario_nominal_approve()
    scenario_nominal_decline()
    scenario_friction_band()
    scenario_timeout_failclosed_default()
    scenario_timeout_failopen_exception()
    scenario_timeout_boundary_enforced()
    scenario_stale_cache_treated_as_untrusted()
    scenario_adversarial_tier2_rejected()
    scenario_threshold_attribution()
    scenario_audit_failure_forces_failclosed()
    scenario_unconfirmed_cluster_no_effect()
    scenario_confirmed_registry_shifts_via_threshold()
    scenario_expired_registry_no_effect()
    scenario_registry_cannot_force_tier2()
    print("=" * 70)
    print("All scenarios executed. Review PASS/FAIL above against the ADRs.")
    print("=" * 70)


if __name__ == "__main__":
    run_all()