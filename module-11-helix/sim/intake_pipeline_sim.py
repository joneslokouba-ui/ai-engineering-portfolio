"""
Module 11 — HELIX: Intake Pipeline Simulation
================================================
Discrete-event simulation of the variant/case intake pipeline:

    Sample intake -> Category router -> Sub-model classification
    -> Clinician review queue

UPDATE (post sub-model + router build): this simulation now runs against
the REAL five sub-models via category_router.route_case(), using
case_generator.py to produce plausible per-category input data in place
of the not-yet-built ingestion layer. stub_classify() is retained below,
unused by the default run path, purely as a reference for the
timing-only mode this module started from (see ADR 011 build history).

Run directly for a console summary:
    python intake_pipeline_sim.py
"""

from __future__ import annotations

import random
import statistics
from dataclasses import dataclass, field
from enum import Enum

import simpy


# ---------------------------------------------------------------------------
# Disorder categories and stub scoring behavior
# ---------------------------------------------------------------------------

class Category(str, Enum):
    MONOGENIC = "Monogenic"
    CHROMOSOMAL = "Chromosomal"
    MULTIFACTORIAL = "Multifactorial"
    XLINKED = "X-linked"
    MITOCHONDRIAL = "Mitochondrial"


# Relative arrival mix — approximates real-world case distribution
# (monogenic and X-linked single-variant cases are the most commonly
# tested; multifactorial/PRS and mitochondrial are rarer in a typical
# diagnostic lab intake stream). This is illustrative, not epidemiological.
CATEGORY_WEIGHTS: dict[Category, float] = {
    Category.MONOGENIC: 0.35,
    Category.CHROMOSOMAL: 0.15,
    Category.MULTIFACTORIAL: 0.20,
    Category.XLINKED: 0.20,
    Category.MITOCHONDRIAL: 0.10,
}

# Stub processing time per category (minutes of simulated compute), reflecting
# relative model complexity. Real models will replace these constants with
# actual scoring latency once implemented.
STUB_PROCESSING_TIME: dict[Category, tuple[float, float]] = {
    # (mean, stddev) — lognormal-ish via random.gauss, floored at 0.5
    Category.MONOGENIC: (2.0, 0.4),
    Category.CHROMOSOMAL: (1.5, 0.3),       # karyotype lookup — fast
    Category.MULTIFACTORIAL: (4.0, 1.0),    # PRS aggregation — slowest
    Category.XLINKED: (2.5, 0.5),
    Category.MITOCHONDRIAL: (3.5, 0.8),     # heteroplasmy handling — slower
}

TIER_OUTCOMES = ["Benign", "VUS", "Pathogenic"]


def stub_classify(category: Category, rng: random.Random) -> tuple[str, float]:
    """
    Deterministic-shape stub scoring function.

    Returns (tier, processing_time_minutes). This is intentionally NOT the
    real classification logic — it exists purely so pipeline throughput,
    routing, and queueing behavior can be validated independently of model
    accuracy work.
    """
    mean, sd = STUB_PROCESSING_TIME[category]
    processing_time = max(0.5, rng.gauss(mean, sd))
    tier = rng.choices(TIER_OUTCOMES, weights=[0.6, 0.3, 0.1])[0]
    return tier, processing_time


# ---------------------------------------------------------------------------
# Metrics collection
# ---------------------------------------------------------------------------

@dataclass
class CaseRecord:
    case_id: int
    category: Category
    arrival_time: float
    routed_time: float = 0.0
    classified_time: float = 0.0
    reviewed_time: float = 0.0
    tier: str = ""              # normalized summary_label from the router
    matched: bool = True        # False = VUS / unrecognized / no confident call

    @property
    def wait_for_router(self) -> float:
        return self.routed_time - self.arrival_time

    @property
    def classification_time(self) -> float:
        return self.classified_time - self.routed_time

    @property
    def review_wait(self) -> float:
        return self.reviewed_time - self.classified_time

    @property
    def total_time_in_system(self) -> float:
        return self.reviewed_time - self.arrival_time


@dataclass
class PipelineMetrics:
    records: list[CaseRecord] = field(default_factory=list)

    def add(self, record: CaseRecord) -> None:
        self.records.append(record)

    def by_category(self) -> dict[Category, list[CaseRecord]]:
        grouped: dict[Category, list[CaseRecord]] = {c: [] for c in Category}
        for r in self.records:
            grouped[r.category].append(r)
        return grouped

    def summary(self) -> str:
        lines = [
            "=" * 90,
            "HELIX Intake Pipeline — Simulation Summary (real sub-models via category_router)",
            "=" * 90,
            f"{'Category':<16}{'Cases':>7}{'Matched %':>11}{'Avg Class. (min)':>20}"
            f"{'Avg Review Wait':>18}{'Avg Total (min)':>18}",
            "-" * 90,
        ]
        grouped = self.by_category()
        for cat in Category:
            recs = grouped[cat]
            if not recs:
                lines.append(f"{cat.value:<16}{0:>7}{'--':>11}{'--':>20}{'--':>18}{'--':>18}")
                continue
            matched_pct = 100.0 * sum(1 for r in recs if r.matched) / len(recs)
            avg_class = statistics.mean(r.classification_time for r in recs)
            avg_review = statistics.mean(r.review_wait for r in recs)
            avg_total = statistics.mean(r.total_time_in_system for r in recs)
            lines.append(
                f"{cat.value:<16}{len(recs):>7}{matched_pct:>10.1f}%{avg_class:>20.2f}"
                f"{avg_review:>18.2f}{avg_total:>18.2f}"
            )
        lines.append("-" * 90)
        total = len(self.records)
        overall_avg_total = (
            statistics.mean(r.total_time_in_system for r in self.records)
            if self.records else 0.0
        )
        lines.append(f"{'TOTAL':<16}{total:>7}{'':>20}{'':>18}{overall_avg_total:>18.2f}")
        lines.append("=" * 72)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Simulation processes
# ---------------------------------------------------------------------------

def case_arrival_process(
    env: simpy.Environment,
    review_queue: simpy.Resource,
    metrics: PipelineMetrics,
    rng: random.Random,
    mean_interarrival: float,
    num_cases: int,
) -> simpy.events.ProcessGenerator:
    """Generates incoming cases at random intervals and routes each one."""
    categories = list(CATEGORY_WEIGHTS.keys())
    weights = list(CATEGORY_WEIGHTS.values())

    for case_id in range(1, num_cases + 1):
        interarrival = rng.expovariate(1.0 / mean_interarrival)
        yield env.timeout(interarrival)

        category = rng.choices(categories, weights=weights)[0]
        record = CaseRecord(
            case_id=case_id, category=category, arrival_time=env.now
        )
        env.process(
            route_and_classify(env, review_queue, metrics, rng, record)
        )


def route_and_classify(
    env: simpy.Environment,
    review_queue: simpy.Resource,
    metrics: PipelineMetrics,
    rng: random.Random,
    record: CaseRecord,
) -> simpy.events.ProcessGenerator:
    """
    Routes a case to its category sub-model via the REAL category_router,
    then queues it for clinician review. case_generator.py produces the
    input data in place of the not-yet-built ingestion layer; processing
    time remains a simulated-turnaround constant per category (lab
    turnaround time, not classification compute cost — the real models
    run in well under a millisecond).
    """
    # Local imports to avoid a circular import at module load time
    # (case_generator imports Category from this module).
    from sim.case_generator import generate_case
    from src.routing.category_router import route_case

    record.routed_time = env.now

    case_input = generate_case(record.category, rng)
    routed_result = route_case(case_input)
    record.tier = routed_result.summary_label
    record.matched = routed_result.matched

    _, processing_time = stub_classify(record.category, rng)
    yield env.timeout(processing_time)
    record.classified_time = env.now

    # Clinician review queue — shared resource, models capacity constraint
    with review_queue.request() as req:
        yield req
        review_duration = max(1.0, rng.gauss(5.0, 1.5))
        yield env.timeout(review_duration)
        record.reviewed_time = env.now

    metrics.add(record)


# ---------------------------------------------------------------------------
# Simulation runner
# ---------------------------------------------------------------------------

def run_simulation(
    num_cases: int = 200,
    mean_interarrival: float = 3.0,
    num_clinician_reviewers: int = 2,
    seed: int = 42,
) -> PipelineMetrics:
    """
    Runs the HELIX intake pipeline simulation.

    Args:
        num_cases: total number of cases to simulate through the pipeline.
        mean_interarrival: mean minutes between case arrivals (Poisson process).
        num_clinician_reviewers: capacity of the shared clinician review queue —
            this is the deliberate bottleneck resource in the pipeline.
        seed: RNG seed for reproducibility.

    Returns:
        PipelineMetrics populated with one CaseRecord per completed case.
    """
    rng = random.Random(seed)
    env = simpy.Environment()
    review_queue = simpy.Resource(env, capacity=num_clinician_reviewers)
    metrics = PipelineMetrics()

    env.process(
        case_arrival_process(
            env, review_queue, metrics, rng, mean_interarrival, num_cases
        )
    )

    # Run until all arrivals have been generated and processed.
    # Upper bound on sim time prevents a hang if queueing blows up.
    env.run(until=mean_interarrival * num_cases * 20)

    return metrics


if __name__ == "__main__":
    metrics = run_simulation(
        num_cases=200,
        mean_interarrival=3.0,
        num_clinician_reviewers=2,
        seed=42,
    )
    print(metrics.summary())

    completed = len(metrics.records)
    print(f"\nCompleted {completed}/200 cases within simulation window.")
    if completed < 200:
        print(
            "NOTE: incomplete run suggests the clinician review queue is "
            "under-provisioned relative to arrival rate — this is exactly "
            "the kind of backlog signal the dashboard should surface, not "
            "a simulation bug. Consider raising num_clinician_reviewers."
        )