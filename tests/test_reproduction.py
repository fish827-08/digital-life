"""Reproduction 繁殖规则测试。"""
from __future__ import annotations

import numpy as np
import pytest

from core.genome import Genome
from core.organism import Organism
from evolution.reproduction import create_offspring
from simulation.config import GenomeConfig, OrganismConfig

ORG_CFG = OrganismConfig()


def make_parent(energy: float = 120.0) -> Organism:
    return Organism(
        organism_id=0,
        x=3,
        y=4,
        genome=Genome(np.linspace(0, 1, 16)),
        config=ORG_CFG,
        energy=energy,
    )


def test_offspring_energy_is_half():
    off = create_offspring(make_parent(energy=120.0), np.random.default_rng(0), GenomeConfig(mutation_rate=0.0))
    assert off.energy == pytest.approx(60.0)


def test_offspring_genome_equals_parent_without_mutation():
    parent = make_parent()
    off = create_offspring(parent, np.random.default_rng(0), GenomeConfig(mutation_rate=0.0))
    assert off.genome == parent.genome


def test_offspring_genome_differs_with_mutation():
    parent = make_parent()
    off = create_offspring(parent, np.random.default_rng(0), GenomeConfig(mutation_rate=1.0, mutation_sigma=0.3))
    assert off.genome != parent.genome


def test_reproduction_is_deterministic():
    parent = make_parent(energy=90.0)
    cfg = GenomeConfig(mutation_rate=0.7, mutation_sigma=0.2)
    a = create_offspring(parent, np.random.default_rng(5), cfg)
    b = create_offspring(parent, np.random.default_rng(5), cfg)
    assert a.genome == b.genome
    assert a.energy == b.energy