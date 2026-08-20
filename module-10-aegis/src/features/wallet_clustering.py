"""
AEGIS — Wallet Clustering
Module 10, ai-engineering-portfolio

Implements a simplified "common-input-ownership" heuristic: wallets that
co-appear as inputs to the same downstream transaction (e.g. multiple
smurf wallets funding one collector) are assumed to be controlled by the
same actor and are grouped into a cluster.

This is a scoped-down version of production clustering techniques used
by chain-analytics firms (e.g. Chainalysis, Elliptic). Production systems
combine dozens of heuristics (change-address detection, temporal
correlation, off-chain leaks); this module demonstrates the core
graph-union-find pattern that underlies them.
"""

from __future__ import annotations

from collections import defaultdict

import pandas as pd


class UnionFind:
    """Standard disjoint-set structure for clustering wallets."""

    def __init__(self):
        self.parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        if x not in self.parent:
            self.parent[x] = x
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x: str, y: str) -> None:
        root_x, root_y = self.find(x), self.find(y)
        if root_x != root_y:
            self.parent[root_x] = root_y


def cluster_wallets(
    ledger: pd.DataFrame, min_shared_dst: int = 1, time_window: int = 30
) -> pd.DataFrame:
    """
    Groups wallets that send funds to a shared destination *within a
    tight time window* (common-input-ownership heuristic).

    NOTE ON DESIGN: an earlier version of this function unioned sources
    that ever shared a destination across the entire ledger. On a
    background-traffic-heavy ledger this causes a giant-component
    collapse — enough random src->dst pairs eventually overlap that
    nearly every wallet merges into one meaningless cluster (validated:
    500/500 wallets collapsed into a single cluster regardless of
    min_shared_dst). Real common-input-ownership only holds when
    multiple sources fund the same destination within the same
    transaction/short interval, not at any point in ledger history —
    hence the added `time_window` constraint.

    Args:
        ledger: transaction DataFrame with src_wallet, dst_wallet,
            timestamp columns.
        min_shared_dst: minimum number of distinct source wallets, within
            the time window, funding the same destination before those
            sources are unioned into a cluster.
        time_window: max timestamp spread (synthetic seconds) between
            transactions considered part of the same funding event.

    Returns:
        DataFrame mapping wallet -> cluster_id, plus cluster_size.
    """
    uf = UnionFind()

    dst_groups: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for _, row in ledger.iterrows():
        dst_groups[row["dst_wallet"]].append((row["timestamp"], row["src_wallet"]))

    for dst, events in dst_groups.items():
        events.sort(key=lambda e: e[0])
        window_srcs: set[str] = set()
        window_start = None
        for ts, src in events:
            if window_start is None or ts - window_start > time_window:
                # flush previous window
                if len(window_srcs) > min_shared_dst:
                    srcs_list = list(window_srcs)
                    for i in range(1, len(srcs_list)):
                        uf.union(srcs_list[0], srcs_list[i])
                window_start = ts
                window_srcs = {src}
            else:
                window_srcs.add(src)
        if len(window_srcs) > min_shared_dst:
            srcs_list = list(window_srcs)
            for i in range(1, len(srcs_list)):
                uf.union(srcs_list[0], srcs_list[i])

    all_wallets = set(ledger["src_wallet"]) | set(ledger["dst_wallet"])
    cluster_map = {w: uf.find(w) for w in all_wallets}

    cluster_sizes: dict[str, int] = defaultdict(int)
    for cluster_id in cluster_map.values():
        cluster_sizes[cluster_id] += 1

    result = pd.DataFrame(
        [
            {"wallet": w, "cluster_id": cid, "cluster_size": cluster_sizes[cid]}
            for w, cid in cluster_map.items()
        ]
    )
    return result


def wallet_cluster_feature(ledger: pd.DataFrame) -> pd.Series:
    """
    Convenience wrapper: returns cluster_size indexed by wallet, for
    joining onto per-transaction feature rows. A large cluster_size on
    the src_wallet side is a smurfing/structuring signal — many distinct
    wallets funneling into one collector look like a single cluster.
    """
    clusters = cluster_wallets(ledger)
    return clusters.set_index("wallet")["cluster_size"]


if __name__ == "__main__":
    from ..ingestion.transaction_simulator import SimulatorConfig, TransactionSimulator

    sim = TransactionSimulator(SimulatorConfig(seed=42))
    ledger = sim.run()

    clusters = cluster_wallets(ledger)
    print(f"Total wallets: {len(clusters)}")
    print(f"Largest clusters:\n{clusters.sort_values('cluster_size', ascending=False).drop_duplicates('cluster_id').head(10)}")