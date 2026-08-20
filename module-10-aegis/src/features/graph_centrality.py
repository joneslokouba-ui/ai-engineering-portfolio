"""
AEGIS — Graph Centrality
Module 10, ai-engineering-portfolio

Builds a directed transaction graph from the ledger and computes
centrality metrics per wallet. Wallets acting as intermediary "hops"
in layering chains typically show high betweenness centrality (many
shortest paths pass through them) despite modest total transaction
volume — a signature that distinguishes them from ordinary high-volume
exchange wallets.
"""

from __future__ import annotations

import networkx as nx
import pandas as pd


def build_transaction_graph(ledger: pd.DataFrame) -> nx.DiGraph:
    """Builds a directed multigraph-collapsed graph from the ledger.

    Edge weight = summed transaction amount between the wallet pair.
    """
    graph = nx.DiGraph()
    for _, row in ledger.iterrows():
        src, dst, amount = row["src_wallet"], row["dst_wallet"], row["amount"]
        if graph.has_edge(src, dst):
            graph[src][dst]["weight"] += amount
            graph[src][dst]["txn_count"] += 1
        else:
            graph.add_edge(src, dst, weight=amount, txn_count=1)
    return graph


def compute_centrality_features(
    ledger: pd.DataFrame, approximate_betweenness_k: int | None = 200
) -> pd.DataFrame:
    """
    Computes graph centrality features per wallet.

    Args:
        ledger: transaction DataFrame.
        approximate_betweenness_k: if set, uses k-sample approximate
            betweenness centrality for performance on large graphs
            (exact betweenness is O(V*E), expensive at scale). None
            forces exact computation.

    Returns:
        DataFrame indexed by wallet with columns:
            - in_degree, out_degree
            - betweenness_centrality (or approximation)
            - degree_centrality
    """
    graph = build_transaction_graph(ledger)

    in_degree = dict(graph.in_degree())
    out_degree = dict(graph.out_degree())
    degree_centrality = nx.degree_centrality(graph)

    k = min(approximate_betweenness_k, graph.number_of_nodes()) if approximate_betweenness_k else None
    betweenness = nx.betweenness_centrality(graph, k=k, weight=None, seed=42)

    wallets = list(graph.nodes())
    features = pd.DataFrame(
        {
            "wallet": wallets,
            "in_degree": [in_degree.get(w, 0) for w in wallets],
            "out_degree": [out_degree.get(w, 0) for w in wallets],
            "degree_centrality": [degree_centrality.get(w, 0.0) for w in wallets],
            "betweenness_centrality": [betweenness.get(w, 0.0) for w in wallets],
        }
    )
    return features


if __name__ == "__main__":
    from ..ingestion.transaction_simulator import SimulatorConfig, TransactionSimulator

    sim = TransactionSimulator(SimulatorConfig(seed=42))
    ledger = sim.run()

    features = compute_centrality_features(ledger)
    print(f"Computed centrality features for {len(features)} wallets")
    print(
        "Top betweenness (likely layering intermediaries):\n",
        features.sort_values("betweenness_centrality", ascending=False).head(10),
    )