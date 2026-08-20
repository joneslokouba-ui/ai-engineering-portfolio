"""
AEGIS — Mixer / Tumbler Proximity
Module 10, ai-engineering-portfolio

Estimates how "close" a wallet is, in hop-distance, to a known or
suspected mixing service. In production this would join against a
curated watchlist of known mixer contract addresses; here we simulate
a small set of designated "mixer" wallets and compute shortest-path
distance from every wallet to the nearest one.

Proximity to a mixer is a strong risk amplifier: funds a few hops from
a tumbler are far more likely to be obfuscated than funds with no
mixer path at all.
"""

from __future__ import annotations

import random

import networkx as nx
import pandas as pd

from .graph_centrality import build_transaction_graph


def designate_mixer_wallets(
    ledger: pd.DataFrame, n_mixers: int = 3, seed: int = 42
) -> list[str]:
    """
    Simulates a watchlist by designating a small number of high-in-degree
    wallets as mixers — a reasonable stand-in, since real mixers
    typically aggregate deposits from many distinct sources.
    """
    rng = random.Random(seed)
    graph = build_transaction_graph(ledger)
    in_degrees = sorted(graph.in_degree(), key=lambda x: x[1], reverse=True)
    candidates = [w for w, _ in in_degrees[:50]]
    if not candidates:
        return []
    return rng.sample(candidates, min(n_mixers, len(candidates)))


def compute_mixer_proximity(
    ledger: pd.DataFrame, mixer_wallets: list[str] | None = None
) -> pd.DataFrame:
    """
    Computes shortest undirected hop-distance from every wallet to the
    nearest designated mixer wallet.

    Args:
        ledger: transaction DataFrame.
        mixer_wallets: known/suspected mixer addresses. If None, a
            synthetic watchlist is auto-designated via
            `designate_mixer_wallets`.

    Returns:
        DataFrame indexed by wallet with columns:
            - mixer_hop_distance (int, -1 if unreachable)
            - mixer_proximity_score (float in [0, 1], 1.0 = direct
              counterparty of a mixer, decaying with distance)
    """
    if mixer_wallets is None:
        mixer_wallets = designate_mixer_wallets(ledger)

    graph = build_transaction_graph(ledger)
    undirected = graph.to_undirected()

    all_wallets = list(undirected.nodes())
    distances: dict[str, int] = {w: -1 for w in all_wallets}

    for mixer in mixer_wallets:
        if mixer not in undirected:
            continue
        lengths = nx.single_source_shortest_path_length(undirected, mixer)
        for wallet, dist in lengths.items():
            if distances[wallet] == -1 or dist < distances[wallet]:
                distances[wallet] = dist

    def proximity_score(dist: int) -> float:
        if dist < 0:
            return 0.0
        return round(1.0 / (1.0 + dist), 4)

    result = pd.DataFrame(
        {
            "wallet": all_wallets,
            "mixer_hop_distance": [distances[w] for w in all_wallets],
            "mixer_proximity_score": [proximity_score(distances[w]) for w in all_wallets],
            "is_designated_mixer": [w in mixer_wallets for w in all_wallets],
        }
    )
    return result


if __name__ == "__main__":
    from ..ingestion.transaction_simulator import SimulatorConfig, TransactionSimulator

    sim = TransactionSimulator(SimulatorConfig(seed=42))
    ledger = sim.run()

    mixers = designate_mixer_wallets(ledger)
    print(f"Designated mixer wallets: {mixers}")

    proximity = compute_mixer_proximity(ledger, mixers)
    print(proximity.sort_values("mixer_proximity_score", ascending=False).head(10))