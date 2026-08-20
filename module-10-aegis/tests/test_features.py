"""
AEGIS — Feature Engineering Tests
Module 10, ai-engineering-portfolio
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from src.ingestion.transaction_simulator import SimulatorConfig, TransactionSimulator
from src.features.wallet_clustering import cluster_wallets
from src.features.velocity import compute_velocity_features
from src.features.graph_centrality import compute_centrality_features, build_transaction_graph
from src.features.mixer_proximity import compute_mixer_proximity, designate_mixer_wallets


@pytest.fixture(scope="module")
def ledger():
    sim = TransactionSimulator(SimulatorConfig(seed=42))
    return sim.run()


class TestWalletClustering:
    def test_no_giant_component_collapse(self, ledger):
        """Regression test for the giant-component bug found during
        development: with a sane time window, no cluster should contain
        anywhere near all wallets in the ledger."""
        clusters = cluster_wallets(ledger, min_shared_dst=1, time_window=60)
        total_wallets = len(clusters)
        max_cluster = clusters["cluster_size"].max()
        assert max_cluster < total_wallets * 0.1, (
            f"Cluster of size {max_cluster} out of {total_wallets} wallets "
            "suggests the giant-component collapse bug has regressed."
        )

    def test_known_smurfing_case_clusters_together(self, ledger):
        """All wallets in a real smurfing case should land in the same
        cluster -- this is the entire point of the heuristic."""
        smurf_txns = ledger[ledger["typology"] == "smurfing"]
        sample_case = smurf_txns["case_id"].iloc[0]
        case_wallets = set(smurf_txns[smurf_txns["case_id"] == sample_case]["src_wallet"])

        clusters = cluster_wallets(ledger, min_shared_dst=1, time_window=60)
        cluster_lookup = clusters.set_index("wallet")["cluster_id"]
        cluster_ids = {cluster_lookup.get(w) for w in case_wallets}
        assert len(cluster_ids) == 1, "Smurfing case wallets split across multiple clusters."

    def test_every_wallet_gets_a_cluster(self, ledger):
        clusters = cluster_wallets(ledger)
        all_wallets = set(ledger["src_wallet"]) | set(ledger["dst_wallet"])
        assert set(clusters["wallet"]) == all_wallets


class TestVelocity:
    def test_output_covers_all_wallets(self, ledger):
        features = compute_velocity_features(ledger)
        all_wallets = set(ledger["src_wallet"]) | set(ledger["dst_wallet"])
        assert set(features["wallet"]) == all_wallets

    def test_pass_through_ratio_bounded(self, ledger):
        features = compute_velocity_features(ledger)
        assert (features["pass_through_ratio"] >= 0).all()
        assert (features["pass_through_ratio"] <= 1.0001).all()  # small float tolerance

    def test_pure_source_or_sink_gets_negative_hold_time(self, ledger):
        """A wallet with only outflow or only inflow has no valid
        in->out pair, so avg_hold_time should be the -1.0 sentinel."""
        features = compute_velocity_features(ledger).set_index("wallet")
        pure_sinks = features[(features["outflow_count"] == 0) & (features["inflow_count"] > 0)]
        if len(pure_sinks) > 0:
            assert (pure_sinks["avg_hold_time"] == -1.0).all()


class TestGraphCentrality:
    def test_output_covers_graph_nodes(self, ledger):
        graph = build_transaction_graph(ledger)
        features = compute_centrality_features(ledger, approximate_betweenness_k=50)
        assert set(features["wallet"]) == set(graph.nodes())

    def test_betweenness_nonnegative(self, ledger):
        features = compute_centrality_features(ledger, approximate_betweenness_k=50)
        assert (features["betweenness_centrality"] >= 0).all()

    def test_degree_centrality_bounded(self, ledger):
        features = compute_centrality_features(ledger, approximate_betweenness_k=50)
        assert (features["degree_centrality"] >= 0).all()
        assert (features["degree_centrality"] <= 1.0001).all()


class TestMixerProximity:
    def test_designated_mixers_have_zero_distance(self, ledger):
        mixers = designate_mixer_wallets(ledger)
        proximity = compute_mixer_proximity(ledger, mixers).set_index("wallet")
        for mixer in mixers:
            assert proximity.loc[mixer, "mixer_hop_distance"] == 0
            assert proximity.loc[mixer, "mixer_proximity_score"] == 1.0

    def test_proximity_score_decays_with_distance(self, ledger):
        mixers = designate_mixer_wallets(ledger)
        proximity = compute_mixer_proximity(ledger, mixers)
        reachable = proximity[proximity["mixer_hop_distance"] >= 0]
        # score should be monotonically non-increasing as distance increases
        grouped = reachable.groupby("mixer_hop_distance")["mixer_proximity_score"].mean()
        distances = sorted(grouped.index)
        scores = [grouped[d] for d in distances]
        assert scores == sorted(scores, reverse=True)

    def test_unreachable_wallets_get_zero_score(self):
        """A wallet with no path to any mixer should score 0.0, not
        raise or produce a negative/undefined value."""
        import pandas as pd
        tiny_ledger = pd.DataFrame([
            {"src_wallet": "A", "dst_wallet": "B", "amount": 100, "timestamp": 1},
            {"src_wallet": "C", "dst_wallet": "D", "amount": 100, "timestamp": 2},
        ])
        proximity = compute_mixer_proximity(tiny_ledger, mixer_wallets=["A"]).set_index("wallet")
        assert proximity.loc["C", "mixer_hop_distance"] == -1
        assert proximity.loc["C", "mixer_proximity_score"] == 0.0