"""
AEGIS — Discrete-Event Simulation Engine
Module 10, ai-engineering-portfolio

Orchestrates the full pipeline end to end across multiple independent
scenario runs (varying seeds), mirroring the validation approach used
across the portfolio (P1's CUSUM threshold tuning, Vigil's full
scenario pass rates): generate ledger -> assemble features -> train/
score ensemble -> sanctions screen -> composite score -> escalate
through the AuthorityBoundary -> measure whether every known injected
typology case was actually detected and escalated.

This is the module's acceptance test: it answers "does AEGIS, running
as a whole system, actually catch the laundering cases it was
designed to catch?" -- not just "does each component run without
crashing?"
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ..ingestion.transaction_simulator import SimulatorConfig, TransactionSimulator
from ..scoring.ensemble_classifier import assemble_features, train_and_validate
from ..scoring.sanctions_matcher import build_synthetic_watchlist, screen_wallets
from ..scoring.composite_score import compute_composite_score
from ..features.mixer_proximity import designate_mixer_wallets
from ..governance.authority_boundary import AuthorityBoundary


ESCALATION_THRESHOLD = 0.6  # composite_score >= this triggers Tier 2 escalation


@dataclass
class ScenarioResult:
    seed: int
    n_transactions: int
    n_wallets: int
    ensemble_auc: float
    n_cases_injected: int
    n_cases_detected: int
    detection_rate: float
    n_escalations: int
    n_false_escalations: int  # escalated wallets with no laundering involvement
    undetected_cases: list[str]


def _case_wallets(ledger: pd.DataFrame) -> dict[str, set[str]]:
    """Maps each injected case_id to the full set of wallets involved."""
    laundering = ledger[ledger["case_id"].notna()]
    mapping: dict[str, set[str]] = {}
    for case_id, group in laundering.groupby("case_id"):
        mapping[case_id] = set(group["src_wallet"]) | set(group["dst_wallet"])
    return mapping


def run_scenario(seed: int, config_overrides: dict | None = None) -> tuple[ScenarioResult, AuthorityBoundary]:
    """
    Runs one full end-to-end scenario: generate -> score -> escalate.
    Returns both the summary result and the populated AuthorityBoundary
    (so a caller can inspect/adjudicate the actual escalation queue).
    """
    config = SimulatorConfig(seed=seed, **(config_overrides or {}))
    sim = TransactionSimulator(config)
    ledger = sim.run()

    features = assemble_features(ledger)
    clf, metrics = train_and_validate(features)

    full_scores = clf.predict_proba(features)
    full_scores.index = features["wallet"].values

    watchlist = build_synthetic_watchlist(ledger, seed=seed + 1000)
    mixers = set(designate_mixer_wallets(ledger, seed=seed))
    screening = screen_wallets(ledger, watchlist, mixers)

    composite = compute_composite_score(full_scores, screening)

    # Autonomous Tier 0-2 pipeline: escalate anything over threshold
    boundary = AuthorityBoundary()
    escalated_wallets = set()
    for _, row in composite.iterrows():
        if row["composite_score"] >= ESCALATION_THRESHOLD:
            boundary.escalate(
                wallet=row["wallet"],
                composite_score=row["composite_score"],
                risk_tier=row["risk_tier"],
                evidence={
                    "ml_score": row["ml_score"],
                    "sanctions_rule_score": row["sanctions_rule_score"],
                },
            )
            escalated_wallets.add(row["wallet"])

    # Detection accounting: was each injected case's wallet set touched
    # by at least one escalation?
    case_map = _case_wallets(ledger)
    detected_cases = []
    undetected_cases = []
    for case_id, wallets in case_map.items():
        if wallets & escalated_wallets:
            detected_cases.append(case_id)
        else:
            undetected_cases.append(case_id)

    all_laundering_wallets = set().union(*case_map.values()) if case_map else set()
    false_escalations = escalated_wallets - all_laundering_wallets

    result = ScenarioResult(
        seed=seed,
        n_transactions=len(ledger),
        n_wallets=len(features),
        ensemble_auc=metrics["auc"],
        n_cases_injected=len(case_map),
        n_cases_detected=len(detected_cases),
        detection_rate=len(detected_cases) / len(case_map) if case_map else 0.0,
        n_escalations=len(escalated_wallets),
        n_false_escalations=len(false_escalations),
        undetected_cases=undetected_cases,
    )
    return result, boundary


def run_multi_seed_validation(seeds: list[int]) -> pd.DataFrame:
    """
    Runs the full pipeline across multiple independent seeds and
    aggregates results -- the multi-run validation pattern used
    elsewhere in the portfolio to confirm a result isn't a single-seed
    fluke.
    """
    rows = []
    for seed in seeds:
        result, _ = run_scenario(seed)
        rows.append(vars(result))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    summary = run_multi_seed_validation(seeds=[1, 2, 3, 7, 42])
    print(summary[
        ["seed", "n_transactions", "ensemble_auc", "n_cases_injected",
         "n_cases_detected", "detection_rate", "n_escalations", "n_false_escalations"]
    ].to_string(index=False))

    print(f"\nMean detection rate across {len(summary)} independent scenarios: "
          f"{summary['detection_rate'].mean():.1%}")
    print(f"Mean false-escalation count: {summary['n_false_escalations'].mean():.1f}")

    any_undetected = summary[summary["detection_rate"] < 1.0]
    if not any_undetected.empty:
        print(f"\nSeeds with undetected cases: {any_undetected['seed'].tolist()}")