"""
AEGIS — Scoring Tests
Module 10, ai-engineering-portfolio
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import pytest

from src.ingestion.transaction_simulator import SimulatorConfig, TransactionSimulator
from src.scoring.ensemble_classifier import assemble_features, train_and_validate
from src.scoring.sanctions_matcher import build_synthetic_watchlist, screen_wallets
from src.scoring.composite_score import compute_composite_score
from src.features.mixer_proximity import designate_mixer_wallets


@pytest.fixture(scope="module")
def ledger():
    sim = TransactionSimulator(SimulatorConfig(seed=42))
    return sim.run()


@pytest.fixture(scope="module")
def features(ledger):
    return assemble_features(ledger)


class TestEnsembleClassifier:
    def test_auc_is_high_but_not_suspiciously_perfect(self, features):
        """Regression test for the two leakage bugs found during
        development (wallet freshness, amount magnitude). A perfect or
        near-1.000 AUC on this feature set is itself a red flag -- it
        means some feature is trivially encoding the label rather than
        capturing genuine structural signal."""
        _, metrics = train_and_validate(features)
        assert metrics["auc"] > 0.9, "AUC too low -- features may have lost signal."
        assert metrics["auc"] < 0.99999, (
            "AUC suspiciously close to 1.000 -- check for reintroduced "
            "leakage (e.g. wallet freshness or amount magnitude)."
        )

    def test_predict_proba_returns_valid_probabilities(self, features):
        clf, _ = train_and_validate(features)
        scores = clf.predict_proba(features)
        assert (scores >= 0).all() and (scores <= 1).all()

    def test_feature_importance_not_dominated_by_single_feature(self, features):
        """No single feature should account for the overwhelming
        majority of importance -- that's the signature of a leakage
        shortcut rather than genuine multi-signal detection."""
        clf, _ = train_and_validate(features)
        importances = clf.feature_importances()
        assert importances.iloc[0] < 0.6, (
            f"Top feature '{importances.index[0]}' accounts for "
            f"{importances.iloc[0]:.1%} of importance -- possible leakage."
        )


class TestSanctionsMatcher:
    def test_direct_hit_scores_1(self, ledger):
        watchlist = build_synthetic_watchlist(ledger, n_entries=3, seed=1)
        screening = screen_wallets(ledger, watchlist)
        for wallet in watchlist:
            row = screening[screening["wallet"] == wallet]
            if not row.empty:
                assert row.iloc[0]["sanctions_rule_score"] == 1.0
                assert row.iloc[0]["watchlist_hit"] == True  # noqa: E712

    def test_non_hit_scores_0(self, ledger):
        watchlist = build_synthetic_watchlist(ledger, n_entries=1, seed=1)
        screening = screen_wallets(ledger, watchlist)
        clean = screening[
            ~screening["watchlist_hit"] & ~screening["watchlist_counterparty_hit"]
        ]
        assert (clean["sanctions_rule_score"] == 0.0).all()


class TestCompositeScore:
    def test_rule_floor_guarantee(self, ledger, features):
        """A direct watchlist hit must force composite_score to 1.0
        regardless of what the ML model scored that wallet -- this is
        the compliance-critical guarantee documented in the ADR."""
        # Force a laundering-uninvolved wallet onto the watchlist so we
        # know the ML component alone would score it low.
        clean_wallet = features[~features["is_laundering"]]["wallet"].iloc[0]
        watchlist = {clean_wallet}

        clf, _ = train_and_validate(features)
        ml_scores = clf.predict_proba(features)
        ml_scores.index = features["wallet"].values

        screening = screen_wallets(ledger, watchlist)
        composite = compute_composite_score(ml_scores, screening).set_index("wallet")

        assert composite.loc[clean_wallet, "composite_score"] == 1.0
        assert composite.loc[clean_wallet, "risk_tier"] == "CRITICAL"

    def test_composite_never_below_blended(self):
        """composite_score = max(blended, rule) by construction -- it
        should never fall below the blended weighted average."""
        ml_scores = pd.Series({"w1": 0.5, "w2": 0.1})
        screening = pd.DataFrame(
            {"wallet": ["w1", "w2"], "sanctions_rule_score": [0.0, 0.6]}
        )
        composite = compute_composite_score(ml_scores, screening).set_index("wallet")
        assert composite.loc["w1", "composite_score"] >= composite.loc["w1", "blended_score"]
        assert composite.loc["w2", "composite_score"] >= composite.loc["w2", "blended_score"]

    def test_risk_tier_thresholds(self):
        # NOTE: with default weights (ml_weight=0.7), blended_score from
        # ML alone tops out at 0.7 -- CRITICAL (threshold 0.85) is
        # reachable only via a sanctions rule hit, by design (see the
        # DESIGN NOTE in composite_score.py). So "critical" here is
        # driven by the rule floor, not raw ML confidence.
        ml_scores = pd.Series({"critical": 0.5, "high": 0.9, "medium": 0.6, "low": 0.1})
        screening = pd.DataFrame(
            {
                "wallet": ["critical", "high", "medium", "low"],
                "sanctions_rule_score": [1.0, 0.0, 0.0, 0.0],
            }
        )
        composite = compute_composite_score(ml_scores, screening).set_index("wallet")
        assert composite.loc["critical", "risk_tier"] == "CRITICAL"
        assert composite.loc["high", "risk_tier"] == "HIGH"
        assert composite.loc["medium", "risk_tier"] == "MEDIUM"
        assert composite.loc["low", "risk_tier"] == "LOW"

    def test_critical_unreachable_by_ml_confidence_alone(self):
        """Documents the intentional design property: even ml_score=1.0
        with zero sanctions signal should NOT reach CRITICAL."""
        ml_scores = pd.Series({"very_confident": 1.0})
        screening = pd.DataFrame({"wallet": ["very_confident"], "sanctions_rule_score": [0.0]})
        composite = compute_composite_score(ml_scores, screening).set_index("wallet")
        assert composite.loc["very_confident", "risk_tier"] != "CRITICAL"