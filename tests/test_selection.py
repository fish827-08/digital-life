"""Selection 选择压判定测试。"""
from __future__ import annotations

import numpy as np

from core.genome import Genome
from core.lifecycle import DeathCause, Lifecycle
from core.organism import Organism
from evolution import selection
from simulation.config import OrganismConfig

CFG = OrganismConfig()


def make_org(*, gene2: float = 1.0, gene3: float = 1.0, energy: float, age: int = 0) -> Organism:
    """gene2→repro_fraction，gene3→life_span；energy/age 可指定。"""
    genes = np.full(16, 0.5)
    genes[2] = gene2
    genes[3] = gene3
    return Organism(
        organism_id=0,
        x=0,
        y=0,
        genome=Genome(genes),
        config=CFG,
        energy=energy,
        lifecycle=Lifecycle(initial_age=age),
    )


def test_repro_threshold_high_energy():
    # gene2=1.0 → repro_fraction=0.9 → 阈值 270
    assert selection.wants_to_reproduce(make_org(energy=280.0), CFG)
    assert not selection.wants_to_reproduce(make_org(energy=100.0), CFG)


def test_repro_threshold_low_fraction():
    # gene2=0.0 → repro_fraction=0.25 → 阈值 75
    assert selection.wants_to_reproduce(make_org(gene2=0.0, energy=100.0), CFG)
    assert not selection.wants_to_reproduce(make_org(gene2=0.0, energy=50.0), CFG)


def test_death_by_starvation():
    assert selection.death_cause_of(make_org(energy=0.0)) is DeathCause.STARVATION
    assert selection.death_cause_of(make_org(energy=-5.0)) is DeathCause.STARVATION


def test_death_by_old_age():
    # gene3=1.0 → life_span=4000；4000 岁且能量充足 → 老死
    org = make_org(energy=1000.0, age=4000)
    assert selection.death_cause_of(org) is DeathCause.OLD_AGE
    young = make_org(energy=1000.0, age=3999)
    assert selection.death_cause_of(young) is None


def test_starvation_takes_precedence_over_old_age():
    org = make_org(energy=0.0, age=4000)  # 又饿又老 → 计为饿死
    assert selection.death_cause_of(org) is DeathCause.STARVATION


def test_alive_individual_returns_none():
    assert selection.death_cause_of(make_org(energy=150.0, age=10)) is None