"""
AEGIS — Sanctions / Watchlist Matcher
Module 10, ai-engineering-portfolio

Rule-based screening against a synthetic sanctions/watchlist (stand-in
for real-world lists like OFAC SDN, UN Consolidated List). This is
deliberately kept as a deterministic rule engine, not a learned model —
sanctions screening is a compliance-critical, auditable function where
false negatives carry regulatory consequence, so exact-match logic is
the correct design choice, not a modeling shortcut.

Also flags direct-mixer-interaction as a rule-based hit, since
transacting directly with a designated mixer is treated as a hard
signal independent of the learned ensemble score.
"""

from __future__ import annotations

import pandas as pd


def build_synthetic_watchlist(
    ledger: pd.DataFrame, n_entries: int = 5, seed: int = 7
) -> set[str]:
    """
    Simulates a sanctions watchlist by designating a small, fixed set of
    wallets as "listed." In production this would be an ingested,
    regularly-updated feed (OFAC SDN list, etc.), not derived from the
    ledger itself.
    """
    import random

    rng = random.Random(seed)
    all_wallets = list(set(ledger["src_wallet"]) | set(ledger["dst_wallet"]))
    return set(rng.sample(all_wallets, min(n_entries, len(all_wallets))))


def screen_wallets(
    ledger: pd.DataFrame,
    watchlist: set[str],
    mixer_wallets: set[str] | None = None,
) -> pd.DataFrame:
    """
    Screens every wallet in the ledger against the watchlist and
    (optionally) direct mixer interaction.

    Returns:
        DataFrame indexed by wallet with columns:
            - watchlist_hit (bool): wallet itself is on the list
            - watchlist_counterparty_hit (bool): wallet has directly
              transacted with a listed wallet
            - direct_mixer_hit (bool): wallet has directly transacted
              with a designated mixer wallet
            - sanctions_rule_score (float, 0.0 / 0.6 / 1.0): deterministic
              rule score — 1.0 for a direct hit, 0.6 for a counterparty
              hit, 0.0 otherwise
    """
    mixer_wallets = mixer_wallets or set()
    all_wallets = set(ledger["src_wallet"]) | set(ledger["dst_wallet"])

    counterparties: dict[str, set[str]] = {w: set() for w in all_wallets}
    for _, row in ledger.iterrows():
        counterparties[row["src_wallet"]].add(row["dst_wallet"])
        counterparties[row["dst_wallet"]].add(row["src_wallet"])

    rows = []
    for wallet in all_wallets:
        direct_hit = wallet in watchlist
        counterparty_hit = bool(counterparties[wallet] & watchlist) and not direct_hit
        mixer_hit = bool(counterparties[wallet] & mixer_wallets)

        if direct_hit:
            rule_score = 1.0
        elif counterparty_hit:
            rule_score = 0.6
        else:
            rule_score = 0.0

        rows.append(
            {
                "wallet": wallet,
                "watchlist_hit": direct_hit,
                "watchlist_counterparty_hit": counterparty_hit,
                "direct_mixer_hit": mixer_hit,
                "sanctions_rule_score": rule_score,
            }
        )

    return pd.DataFrame(rows)


if __name__ == "__main__":
    from ..ingestion.transaction_simulator import SimulatorConfig, TransactionSimulator
    from ..features.mixer_proximity import designate_mixer_wallets

    sim = TransactionSimulator(SimulatorConfig(seed=42))
    ledger = sim.run()

    watchlist = build_synthetic_watchlist(ledger)
    mixers = set(designate_mixer_wallets(ledger))

    screening = screen_wallets(ledger, watchlist, mixers)
    print(f"Watchlist size: {len(watchlist)}, Mixer count: {len(mixers)}")
    print(f"Direct hits: {screening['watchlist_hit'].sum()}")
    print(f"Counterparty hits: {screening['watchlist_counterparty_hit'].sum()}")
    print(f"Direct mixer interaction: {screening['direct_mixer_hit'].sum()}")