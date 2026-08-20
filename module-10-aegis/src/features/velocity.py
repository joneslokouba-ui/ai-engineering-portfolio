"""
AEGIS — Velocity Analysis
Module 10, ai-engineering-portfolio

Computes per-wallet transaction velocity features: how fast funds move
in and out of a wallet, and how tightly clustered transaction timing is.
Rapid in-and-out movement with minimal balance retention (a "pass-through"
wallet) is a hallmark of layering and peel-chain typologies.
"""

from __future__ import annotations

import pandas as pd


def compute_velocity_features(
    ledger: pd.DataFrame, window: int | None = None
) -> pd.DataFrame:
    """
    Computes velocity features per wallet.

    Args:
        ledger: transaction DataFrame with src_wallet, dst_wallet,
            timestamp, amount columns.
        window: optional rolling time window (in synthetic seconds) to
            restrict velocity calculation to recent activity. None uses
            the full ledger.

    Returns:
        DataFrame indexed by wallet with columns:
            - inflow_count, outflow_count
            - inflow_amount, outflow_amount
            - net_flow (inflow_amount - outflow_amount)
            - pass_through_ratio (min(in,out) / max(in,out) amount —
              close to 1.0 means funds pass straight through)
            - avg_hold_time (mean seconds between an inflow and the next
              outflow — short hold time is a layering/peel-chain signal)
    """
    df = ledger.copy()
    if window is not None:
        cutoff = df["timestamp"].max() - window
        df = df[df["timestamp"] >= cutoff]

    inflows = df.groupby("dst_wallet").agg(
        inflow_count=("txn_id", "count"), inflow_amount=("amount", "sum")
    )
    outflows = df.groupby("src_wallet").agg(
        outflow_count=("txn_id", "count"), outflow_amount=("amount", "sum")
    )

    features = inflows.join(outflows, how="outer").fillna(0.0)
    features.index.name = "wallet"

    features["net_flow"] = features["inflow_amount"] - features["outflow_amount"]

    max_amt = features[["inflow_amount", "outflow_amount"]].max(axis=1)
    min_amt = features[["inflow_amount", "outflow_amount"]].min(axis=1)
    features["pass_through_ratio"] = (min_amt / max_amt.replace(0, pd.NA)).fillna(0.0)

    features["avg_hold_time"] = features.index.map(
        lambda w: _avg_hold_time(df, w)
    )

    return features.reset_index()


def _avg_hold_time(ledger: pd.DataFrame, wallet: str) -> float:
    """
    Mean time between each inbound transaction to `wallet` and the next
    outbound transaction from `wallet`. Returns -1.0 if the wallet has
    no qualifying in/out pair (pure sink or pure source).
    """
    inbound = ledger[ledger["dst_wallet"] == wallet]["timestamp"].sort_values()
    outbound = ledger[ledger["src_wallet"] == wallet]["timestamp"].sort_values()

    if inbound.empty or outbound.empty:
        return -1.0

    gaps = []
    outbound_list = outbound.tolist()
    for in_ts in inbound:
        next_out = next((o for o in outbound_list if o >= in_ts), None)
        if next_out is not None:
            gaps.append(next_out - in_ts)

    return sum(gaps) / len(gaps) if gaps else -1.0


if __name__ == "__main__":
    from ..ingestion.transaction_simulator import SimulatorConfig, TransactionSimulator

    sim = TransactionSimulator(SimulatorConfig(seed=42))
    ledger = sim.run()

    features = compute_velocity_features(ledger)
    print(f"Computed velocity features for {len(features)} wallets")
    print(features.sort_values("pass_through_ratio", ascending=False).head(10))