"""
AEGIS — Typology Generator
Module 10, ai-engineering-portfolio

Injected AML typology generators, extracted from TransactionSimulator so
the "what a laundering pattern looks like" logic is independently
readable, testable, and extensible without touching the ledger-assembly
machinery in transaction_simulator.py.

Each generator function takes a `SimulatorContext` (the minimal surface
TransactionSimulator exposes: wallet pool, config, and the `_emit`
helper) and appends one full case's worth of transactions to the
ledger being built. This keeps a single source of truth for the
random-number-generator call sequence (still owned by
TransactionSimulator) while separating typology *design* from ledger
*assembly*.
"""

from __future__ import annotations

import random
import uuid
from typing import Protocol

from ..ingestion.transaction_simulator import Typology, SimulatorConfig, _new_wallet_id


class SimulatorContext(Protocol):
    """Minimal interface a typology generator needs from the simulator."""

    wallets: list[str]
    config: SimulatorConfig

    def _emit(
        self,
        src: str,
        dst: str,
        amount: float,
        typology: Typology,
        case_id: str | None,
        step_gap: int = 1,
    ) -> None: ...


# ---------------------------------------------------------------------
# Typology: Layering
# Funds routed through several intermediary wallets in quick succession
# to obscure origin, before consolidating at a final destination.
# ---------------------------------------------------------------------
def generate_layering_case(sim: SimulatorContext, aged_wallet_fraction: float = 0.4) -> str:
    """Appends one layering case to the ledger being built by `sim`.
    Returns the generated case_id."""
    case_id = f"layering-{uuid.uuid4().hex[:8]}"
    origin = _new_wallet_id()
    destination = _new_wallet_id()
    sim.wallets.extend([origin, destination])

    # Real launderers route through aged, legitimate-looking wallets, not
    # exclusively fresh ones -- mix in pre-existing pool wallets as
    # intermediaries so "wallet freshness" alone isn't a giveaway (see
    # ADR-010 / transaction_simulator.py notes on the wallet-freshness
    # leakage bug this design choice fixes).
    n_hops = random.randint(4, 7)
    intermediaries = [
        random.choice(sim.wallets[: sim.config.n_wallets])
        if random.random() < aged_wallet_fraction
        else _new_wallet_id()
        for _ in range(n_hops)
    ]
    sim.wallets.extend([w for w in intermediaries if w not in sim.wallets])

    amount = random.uniform(2_000, 150_000)
    chain = [origin] + intermediaries + [destination]
    for i in range(len(chain) - 1):
        amount *= random.uniform(0.97, 0.995)  # fees/obfuscation at each hop
        sim._emit(chain[i], chain[i + 1], amount, Typology.LAYERING, case_id, step_gap=2)

    return case_id


# ---------------------------------------------------------------------
# Typology: Peel Chain
# A single large balance is "peeled" -- a small amount is split off to a
# new wallet at each hop while the remainder moves forward, repeated
# across many hops.
# ---------------------------------------------------------------------
def generate_peel_chain_case(sim: SimulatorContext) -> str:
    """Appends one peel-chain case to the ledger being built by `sim`.
    Returns the generated case_id."""
    case_id = f"peel-{uuid.uuid4().hex[:8]}"
    current = _new_wallet_id()
    sim.wallets.append(current)
    remaining = random.uniform(5_000, 300_000)

    n_peels = random.randint(6, 12)
    for _ in range(n_peels):
        peel_wallet = _new_wallet_id()
        sim.wallets.append(peel_wallet)
        peel_amount = remaining * random.uniform(0.05, 0.15)
        remaining -= peel_amount

        next_wallet = _new_wallet_id()
        sim.wallets.append(next_wallet)

        sim._emit(current, peel_wallet, peel_amount, Typology.PEEL_CHAIN, case_id, step_gap=3)
        sim._emit(current, next_wallet, remaining, Typology.PEEL_CHAIN, case_id, step_gap=1)
        current = next_wallet

    return case_id


# ---------------------------------------------------------------------
# Typology: Smurfing / Structuring
# A large sum is split across many small transactions, each kept under a
# reporting threshold, funneled from many source wallets into a common
# collection wallet.
# ---------------------------------------------------------------------
def generate_smurfing_case(
    sim: SimulatorContext,
    reporting_threshold: float = 10_000.0,
    aged_wallet_fraction: float = 0.3,
) -> str:
    """Appends one smurfing case to the ledger being built by `sim`.
    Returns the generated case_id."""
    case_id = f"smurf-{uuid.uuid4().hex[:8]}"
    collector = _new_wallet_id()
    sim.wallets.append(collector)

    n_smurfs = random.randint(8, 20)
    for _ in range(n_smurfs):
        # Mix aged pool wallets in as "smurfs" alongside fresh ones -- real
        # structuring often uses money mules with pre-existing, normal-
        # looking transaction histories.
        if random.random() < aged_wallet_fraction:
            smurf_wallet = random.choice(sim.wallets[: sim.config.n_wallets])
        else:
            smurf_wallet = _new_wallet_id()
            sim.wallets.append(smurf_wallet)
        amount = reporting_threshold * random.uniform(0.6, 0.95)  # stays under threshold
        sim._emit(smurf_wallet, collector, amount, Typology.SMURFING, case_id, step_gap=4)

    return case_id