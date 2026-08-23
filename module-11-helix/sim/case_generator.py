"""
Module 11 — HELIX: Synthetic Case Generator
==============================================
Stands in for the not-yet-built ingestion layer (ingestion/clinvar_loader.py,
gnomad_loader.py, omim_loader.py). Produces plausible random CaseInput
objects per category so the category_router and downstream simulation/
dashboard can be exercised against realistic-shaped data before real
ClinVar/gnomAD/OMIM parsing exists.

This is explicitly a stand-in, not a claim about real-world variant
distributions — random draws here are for pipeline testing, not
epidemiological accuracy. Once the ingestion layer exists, this module
should be replaced (or kept alongside, for load-testing) rather than
mistaken for real data.
"""

from __future__ import annotations

import random

from src.routing.category_router import (
    CaseInput,
    ChromosomalCase,
    MitochondrialCase,
    MonogenicCase,
    MultifactorialCase,
    XLinkedCase,
)
from src.models.monogenic_model import ConsequenceType, ReviewStatus, VariantFeatures
from src.models.multifactorial_model import AlleleDosage, EnvironmentalFactor, PolygenicProfile, RiskAllele
from sim.intake_pipeline_sim import Category
from src.models.xlinked_model import XLinkedFeatures, Zygosity

_CONSEQUENCES = list(ConsequenceType)
_REVIEW_STATUSES = list(ReviewStatus)

_KARYOTYPES = [
    "46,XX", "46,XY",                       # normal — majority of cases
    "47,XX,+21", "47,XY,+21",               # trisomy 21
    "45,X",                                  # Turner
    "47,XX,+21[80]/46,XX[20]",              # mosaic trisomy 21
    "99,ZZ,+99",                             # unrecognized, for testing the no-match path
]

_MITO_VARIANTS = ["m.3243A>G", "m.11778G>A", "m.9999X>Y"]  # last one deliberately unrecognized

_PRS_DISORDERS = ["Type 2 Diabetes", "Coronary Heart Disease"]


def _random_variant_features(rng: random.Random, gene: str) -> VariantFeatures:
    return VariantFeatures(
        gene=gene,
        consequence=rng.choice(_CONSEQUENCES),
        review_status=rng.choice(_REVIEW_STATUSES),
        conservation_score=rng.uniform(0.0, 1.0),
        gnomad_allele_frequency=rng.choice([
            rng.uniform(0.0, 0.0001),   # rare
            rng.uniform(0.0001, 0.01),  # intermediate
            rng.uniform(0.01, 0.2),     # common
        ]),
    )


def generate_monogenic_case(rng: random.Random) -> MonogenicCase:
    gene = rng.choice(["CFTR", "HBB", "HTT"])
    return MonogenicCase(features=_random_variant_features(rng, gene))


def generate_xlinked_case(rng: random.Random) -> XLinkedCase:
    gene = rng.choice(["DMD", "F8"])
    return XLinkedCase(
        features=XLinkedFeatures(
            variant=_random_variant_features(rng, gene),
            zygosity=rng.choice(list(Zygosity)),
        )
    )


def generate_chromosomal_case(rng: random.Random) -> ChromosomalCase:
    return ChromosomalCase(karyotype=rng.choice(_KARYOTYPES))


def generate_multifactorial_case(rng: random.Random) -> MultifactorialCase:
    disorder = rng.choice(_PRS_DISORDERS)
    num_alleles = rng.randint(3, 6)
    dosages = []
    for i in range(num_alleles):
        allele = RiskAllele(
            rsid=f"rs{rng.randint(1000, 9999)}",
            effect_weight=rng.uniform(0.1, 0.6),
            population_allele_frequency=rng.uniform(0.05, 0.5),
        )
        dosages.append(AlleleDosage(allele=allele, dosage=rng.choice([0, 1, 2])))

    num_env_factors = rng.choice([0, 0, 1, 2, 3])  # weighted toward fewer factors
    env_factors = rng.sample(list(EnvironmentalFactor), k=num_env_factors)

    return MultifactorialCase(
        profile=PolygenicProfile(disorder=disorder, dosages=dosages, environmental_factors=env_factors)
    )


def generate_mitochondrial_case(rng: random.Random) -> MitochondrialCase:
    variant_id = rng.choice(_MITO_VARIANTS)
    return MitochondrialCase(variant_id=variant_id, heteroplasmy_pct=rng.uniform(0.0, 100.0))


_GENERATORS = {
    Category.MONOGENIC: generate_monogenic_case,
    Category.XLINKED: generate_xlinked_case,
    Category.CHROMOSOMAL: generate_chromosomal_case,
    Category.MULTIFACTORIAL: generate_multifactorial_case,
    Category.MITOCHONDRIAL: generate_mitochondrial_case,
}


def generate_case(category: Category, rng: random.Random) -> CaseInput:
    """Dispatches to the correct per-category generator."""
    return _GENERATORS[category](rng)