"""
AEGIS — Composite Risk Score
Module 10, ai-engineering-portfolio

Combines the learned ensemble probability with the deterministic
sanctions/watchlist rule score into a single composite risk score per
wallet, mirroring the multi-engine composite scoring pattern used in
the P1 Pipeline Integrity Monitor (corrosion regression -> CUSUM leak
detection -> composite risk score).

Design choice: sanctions hits are NOT simply averaged into the ML
score. A direct watchlist hit is compliance-critical and must dominate
regardless of what the learned model thinks -- so the composite uses a
"rule floor" pattern: the final score is the max of the weighted blend
and the raw sanctions rule score. This guarantees a direct hit never
gets diluted below its own severity by an ML model that happened to
score that wallet as low-risk on structural features alone.
"""

from __future__ import annotations

import pandas as pd


DEFAULT_ML_WEIGHT = 0.7
DEFAULT_RULE_WEIGHT = 0.3

# DESIGN NOTE: with the default weights, the ML-only blended_score tops
# out at ml_weight * 1.0 = 0.7 when sanctions_rule_score is 0. Since the
# CRITICAL threshold below is 0.85, CRITICAL is *intentionally*
# unreachable through model confidence alone -- it can only be reached
# via a direct sanctions/watchlist hit (the rule-floor guarantee) or a
# combination of high ML confidence plus a counterparty rule hit
# (0.6 rule_weight-scaled component). This mirrors real AML practice:
# an algorithm being very confident is not, by itself, grounds for the
# most severe compliance tier -- that tier is reserved for cases with
# a corroborating deterministic signal. If this is ever tuned, verify
# the max-reachable-by-ML-alone value (ml_weight * 1.0) against the
# CRITICAL threshold so this property stays intentional, not accidental.
RISK_TIERS = [
    (0.85, "CRITICAL"),
    (0.6, "HIGH"),
    (0.35, "MEDIUM"),
    (0.0, "LOW"),
]


def compute_composite_score(
    ml_scores: pd.Series,
    sanctions_screening: pd.DataFrame,
    ml_weight: float = DEFAULT_ML_WEIGHT,
    rule_weight: float = DEFAULT_RULE_WEIGHT,
) -> pd.DataFrame:
    """
    Args:
        ml_scores: Series of ensemble predicted probabilities, indexed
            by wallet (from AegisEnsembleClassifier.predict_proba, with
            features['wallet'] as the join key).
        sanctions_screening: DataFrame from screen_wallets(), with
            'wallet' and 'sanctions_rule_score' columns.
        ml_weight, rule_weight: blend weights for the weighted-average
            component (should sum to 1.0; not enforced, allows
            deliberate re-weighting experiments).

    Returns:
        DataFrame indexed by wallet with:
            - ml_score
            - sanctions_rule_score
            - blended_score (weighted average)
            - composite_score (max(blended_score, sanctions_rule_score) --
              the rule-floor guarantee)
            - risk_tier (CRITICAL / HIGH / MEDIUM / LOW)
    """
    screening = sanctions_screening.set_index("wallet")["sanctions_rule_score"]

    combined = pd.DataFrame({"ml_score": ml_scores}).join(
        screening.rename("sanctions_rule_score"), how="outer"
    )
    combined = combined.fillna(0.0)

    combined["blended_score"] = (
        ml_weight * combined["ml_score"] + rule_weight * combined["sanctions_rule_score"]
    )
    combined["composite_score"] = combined[["blended_score", "sanctions_rule_score"]].max(axis=1)
    combined["risk_tier"] = combined["composite_score"].apply(_assign_tier)

    return combined.reset_index().rename(columns={"index": "wallet"})


def _assign_tier(score: float) -> str:
    for threshold, tier in RISK_TIERS:
        if score >= threshold:
            return tier
    return "LOW"


if __name__ == "__main__":
    from ..ingestion.transaction_simulator import SimulatorConfig, TransactionSimulator
    from .ensemble_classifier import assemble_features, train_and_validate
    from .sanctions_matcher import build_synthetic_watchlist, screen_wallets
    from ..features.mixer_proximity import designate_mixer_wallets

    sim = TransactionSimulator(SimulatorConfig(seed=42))
    ledger = sim.run()

    features = assemble_features(ledger)
    clf, metrics = train_and_validate(features)
    print(f"Ensemble ROC-AUC: {metrics['auc']:.4f}\n")

    full_scores = clf.predict_proba(features)
    full_scores.index = features["wallet"].values

    watchlist = build_synthetic_watchlist(ledger)
    mixers = set(designate_mixer_wallets(ledger))
    screening = screen_wallets(ledger, watchlist, mixers)

    composite = compute_composite_score(full_scores, screening)
    print("Risk tier distribution:")
    print(composite["risk_tier"].value_counts())
    print("\nTop 10 highest composite scores:")
    print(
        composite.sort_values("composite_score", ascending=False)
        [["wallet", "ml_score", "sanctions_rule_score", "composite_score", "risk_tier"]]
        .head(10)
    )