"""
AEGIS — Ensemble Risk Classifier
Module 10, ai-engineering-portfolio

Assembles the four feature sets (wallet clustering, velocity, graph
centrality, mixer proximity) into a single per-wallet feature matrix,
trains a gradient-boosted classifier against the simulator's ground-
truth `is_laundering` labels, and exposes a scoring interface.

Ground truth is wallet-level: a wallet is labeled positive if it
appears as src or dst in ANY transaction tagged with a laundering
typology. This is a simplification (real AML labels are typically
transaction- or case-level with analyst adjudication) but is
sufficient to validate that the feature set carries genuine signal.
"""

from __future__ import annotations

import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, precision_recall_curve, classification_report

from ..features.wallet_clustering import cluster_wallets
from ..features.velocity import compute_velocity_features
from ..features.graph_centrality import compute_centrality_features
from ..features.mixer_proximity import compute_mixer_proximity, designate_mixer_wallets


FEATURE_COLUMNS = [
    "cluster_size",
    "inflow_count",
    "outflow_count",
    "inflow_amount",
    "outflow_amount",
    "net_flow",
    "pass_through_ratio",
    "avg_hold_time",
    "in_degree",
    "out_degree",
    "degree_centrality",
    "betweenness_centrality",
    "mixer_hop_distance",
    "mixer_proximity_score",
]


def assemble_features(ledger: pd.DataFrame) -> pd.DataFrame:
    """
    Joins all four feature modules into a single per-wallet DataFrame,
    plus the ground-truth label for training/validation.
    """
    clusters = cluster_wallets(ledger, min_shared_dst=1, time_window=60)[
        ["wallet", "cluster_size"]
    ]
    velocity = compute_velocity_features(ledger)
    centrality = compute_centrality_features(ledger, approximate_betweenness_k=200)
    mixer_wallets = designate_mixer_wallets(ledger)
    proximity = compute_mixer_proximity(ledger, mixer_wallets)[
        ["wallet", "mixer_hop_distance", "mixer_proximity_score"]
    ]

    features = clusters.merge(velocity, on="wallet", how="outer")
    features = features.merge(centrality, on="wallet", how="outer")
    features = features.merge(proximity, on="wallet", how="outer")
    features = features.fillna(0.0)

    laundering_wallets = set(
        ledger.loc[ledger["is_laundering"], "src_wallet"]
    ) | set(ledger.loc[ledger["is_laundering"], "dst_wallet"])
    features["is_laundering"] = features["wallet"].isin(laundering_wallets)

    return features


class AegisEnsembleClassifier:
    """Wraps a GradientBoostingClassifier with a fixed feature contract."""

    def __init__(self, **model_kwargs):
        defaults = dict(
            n_estimators=150,
            max_depth=3,
            learning_rate=0.1,
            random_state=42,
        )
        defaults.update(model_kwargs)
        self.model = GradientBoostingClassifier(**defaults)
        self.is_fitted = False

    def fit(self, features: pd.DataFrame) -> "AegisEnsembleClassifier":
        X = features[FEATURE_COLUMNS]
        y = features["is_laundering"]
        self.model.fit(X, y)
        self.is_fitted = True
        return self

    def predict_proba(self, features: pd.DataFrame) -> pd.Series:
        if not self.is_fitted:
            raise RuntimeError("Model must be fit before scoring.")
        X = features[FEATURE_COLUMNS]
        return pd.Series(self.model.predict_proba(X)[:, 1], index=features.index)

    def feature_importances(self) -> pd.Series:
        if not self.is_fitted:
            raise RuntimeError("Model must be fit before inspecting importances.")
        return pd.Series(
            self.model.feature_importances_, index=FEATURE_COLUMNS
        ).sort_values(ascending=False)


def train_and_validate(features: pd.DataFrame, test_size: float = 0.3):
    """
    Splits features into train/test, fits the ensemble, and returns
    validation metrics. Uses stratified split since laundering wallets
    are a minority class.
    """
    train_df, test_df = train_test_split(
        features, test_size=test_size, stratify=features["is_laundering"], random_state=42
    )

    clf = AegisEnsembleClassifier().fit(train_df)
    test_proba = clf.predict_proba(test_df)
    test_pred = (test_proba >= 0.5).astype(int)

    auc = roc_auc_score(test_df["is_laundering"], test_proba)
    report = classification_report(test_df["is_laundering"], test_pred, digits=3)

    return clf, {"auc": auc, "report": report}


if __name__ == "__main__":
    from ..ingestion.transaction_simulator import SimulatorConfig, TransactionSimulator

    sim = TransactionSimulator(SimulatorConfig(seed=42))
    ledger = sim.run()

    features = assemble_features(ledger)
    print(f"Assembled features for {len(features)} wallets, "
          f"{features['is_laundering'].sum()} positive")

    clf, metrics = train_and_validate(features)
    print(f"\nROC-AUC: {metrics['auc']:.4f}")
    print(f"\n{metrics['report']}")
    print("\nFeature importances:")
    print(clf.feature_importances())