"""
AEGIS — Synthetic Transaction Ledger Generator
Module 10, ai-engineering-portfolio

Generates a synthetic blockchain-style transaction ledger consisting of:
  - Background traffic: ordinary wallet-to-wallet transfers (unlabeled, non-laundering)
  - Injected typologies: layering, peel chains, and smurfing (structuring)

Ground-truth labels are attached to every transaction so downstream scoring
modules (features/, scoring/) can be validated against known laundering
patterns, mirroring the CUSUM validation approach used in Module: P1
Pipeline Integrity Monitor.

Output: pandas DataFrame / CSV with one row per transaction.
"""

from __future__ import annotations

import random
import string
import uuid
from dataclasses import dataclass, field
from enum import Enum

import pandas as pd


class Typology(str, Enum):
    NONE = "none"
    LAYERING = "layering"
    PEEL_CHAIN = "peel_chain"
    SMURFING = "smurfing"


@dataclass
class SimulatorConfig:
    n_wallets: int = 500
    n_background_txns: int = 5000
    n_layering_cases: int = 8
    n_peel_chain_cases: int = 6
    n_smurfing_cases: int = 10
    # Background amounts use a log-normal distribution (not Gaussian) so a
    # realistic minority of ordinary transactions are large -- payroll,
    # business-to-business payments, exchange withdrawals. Earlier version
    # used a tight Gaussian (mean=250, sd=400, max~5.5K) that never
    # overlapped with laundering-case amounts ($20K-$300K), making amount
    # alone a perfect classifier and defeating the purpose of the
    # structural (clustering/centrality/mixer) features this module
    # exists to test. Log-normal params below give a median transaction
    # near ~$300 with a heavy right tail reaching into six figures.
    background_amount_lognorm_mu: float = 5.7
    background_amount_lognorm_sigma: float = 1.6
    seed: int | None = 42


def _new_wallet_id() -> str:
    """Generate a synthetic wallet address (shortened for readability)."""
    return "0x" + "".join(random.choices(string.hexdigits.lower(), k=12))


class TransactionSimulator:
    """
    Discrete-event style generator: builds a pool of wallets, then emits
    a chronological stream of transactions combining ordinary background
    traffic with explicitly injected laundering typologies.
    """

    def __init__(self, config: SimulatorConfig | None = None):
        self.config = config or SimulatorConfig()
        if self.config.seed is not None:
            random.seed(self.config.seed)
        self.wallets: list[str] = [
            _new_wallet_id() for _ in range(self.config.n_wallets)
        ]
        self.timestamp: int = 0  # monotonically increasing synthetic clock (seconds)
        self.rows: list[dict] = []

    # ---------------------------------------------------------------
    # Core emission helper
    # ---------------------------------------------------------------
    def _emit(
        self,
        src: str,
        dst: str,
        amount: float,
        typology: Typology,
        case_id: str | None,
        step_gap: int = 1,
    ) -> None:
        self.timestamp += random.randint(1, step_gap)
        self.rows.append(
            {
                "txn_id": str(uuid.uuid4()),
                "timestamp": self.timestamp,
                "src_wallet": src,
                "dst_wallet": dst,
                "amount": round(amount, 2),
                "typology": typology.value,
                "case_id": case_id,
                "is_laundering": typology != Typology.NONE,
            }
        )

    # ---------------------------------------------------------------
    # Background traffic
    #
    # NOTE ON REALISM: an earlier version drew every background
    # transaction from the same fixed 500-wallet pool, and every
    # laundering wallet was freshly minted and single-use. That made
    # "wallet freshness / low degree" a perfect proxy for the label
    # (validated: out_degree background ~9.9 vs laundering ~0.9,
    # ensemble AUC = 1.000 -- a red flag, not a win, on a compliance
    # model). Real background traffic includes plenty of one-off,
    # low-degree wallets too (e.g. a new user's single deposit), so a
    # fixed fraction of background transactions now use freshly minted,
    # single-use wallets to remove that shortcut and force the ensemble
    # to rely on genuine structural signal (clustering, centrality,
    # mixer proximity) rather than wallet age.
    # ---------------------------------------------------------------
    def _generate_background(self, fresh_wallet_fraction: float = 0.35) -> None:
        for _ in range(self.config.n_background_txns):
            use_fresh = random.random() < fresh_wallet_fraction
            if use_fresh:
                src = _new_wallet_id() if random.random() < 0.5 else random.choice(self.wallets)
                dst = _new_wallet_id() if random.random() < 0.5 else random.choice(self.wallets)
                if src == dst:
                    continue
                self.wallets.append(src) if src not in self.wallets else None
                self.wallets.append(dst) if dst not in self.wallets else None
            else:
                src, dst = random.sample(self.wallets, 2)
            amount = random.lognormvariate(
                self.config.background_amount_lognorm_mu,
                self.config.background_amount_lognorm_sigma,
            )
            amount = min(max(amount, 1.0), 400_000.0)
            self._emit(src, dst, amount, Typology.NONE, case_id=None, step_gap=5)

    # ---------------------------------------------------------------
    # Public entry point
    # ---------------------------------------------------------------
    def run(self) -> pd.DataFrame:
        # Deferred import: typology_generator.py imports Typology and
        # _new_wallet_id from this module, so importing it back here at
        # module level would create a circular import. Deferring to
        # call-time (inside run(), after both modules have finished
        # loading) resolves it cleanly.
        from ..simulation.typology_generator import (
            generate_layering_case,
            generate_peel_chain_case,
            generate_smurfing_case,
        )

        self._generate_background()
        for _ in range(self.config.n_layering_cases):
            generate_layering_case(self)
        for _ in range(self.config.n_peel_chain_cases):
            generate_peel_chain_case(self)
        for _ in range(self.config.n_smurfing_cases):
            generate_smurfing_case(self)

        df = pd.DataFrame(self.rows).sort_values("timestamp").reset_index(drop=True)
        return df

    def run_and_save(self, path: str) -> pd.DataFrame:
        df = self.run()
        df.to_csv(path, index=False)
        return df


if __name__ == "__main__":
    sim = TransactionSimulator(SimulatorConfig())
    ledger = sim.run()
    print(f"Generated {len(ledger)} transactions")
    print(ledger["typology"].value_counts())
    print(f"Laundering rate: {ledger['is_laundering'].mean():.2%}")