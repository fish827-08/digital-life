"""配置模块测试：默认值、边界校验、可复现性基础。"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from simulation.config import (
    GenomeConfig,
    OrganismConfig,
    PopulationConfig,
    ResourceConfig,
    SimConfig,
    WorldConfig,
)


def test_default_config_is_valid():
    cfg = SimConfig()
    assert cfg.seed == 42
    assert cfg.world.width == 128 and cfg.world.height == 128
    assert cfg.population.initial_count <= cfg.population.max_count


def test_roundtrip_preserves_config():
    """存档基础：dict 往返后配置完全一致。"""
    source = SimConfig(
        seed=7,
        world=WorldConfig(width=64, height=64),
        genome=GenomeConfig(gene_count=8, mutation_rate=0.1),
        population=PopulationConfig(initial_count=50, max_count=500),
    )
    restored = SimConfig.from_dict(source.to_dict())
    assert restored == source


def test_fingerprint_is_deterministic_and_sensitive():
    cfg = SimConfig(seed=1)
    assert cfg.fingerprint() == cfg.fingerprint()
    other = SimConfig(seed=1)
    assert cfg.fingerprint() == other.fingerprint()
    other.seed = 2
    assert cfg.fingerprint() != other.fingerprint()


def test_world_size_bounds():
    with pytest.raises(ValidationError):
        WorldConfig(width=2)


def test_mutation_rate_bounds():
    with pytest.raises(ValidationError):
        GenomeConfig(mutation_rate=1.5)


def test_gene_range_must_be_ordered():
    with pytest.raises(ValidationError):
        GenomeConfig(gene_min=0.9, gene_max=0.1)


def test_resource_fill_bounds():
    with pytest.raises(ValidationError):
        ResourceConfig(initial_fill=2.0)


def test_organism_energy_bounds():
    with pytest.raises(ValidationError):
        OrganismConfig(initial_energy=400.0, max_energy=300.0)


def test_population_max_ge_initial():
    with pytest.raises(ValidationError):
        PopulationConfig(initial_count=100, max_count=10)


def test_null_seed_allowed():
    cfg = SimConfig(seed=None)
    assert cfg.seed is None