"""Mutation 策略包装测试。"""
from __future__ import annotations

import numpy as np

from core.genome import Genome
from evolution.mutation import mutate_genome
from simulation.config import GenomeConfig


def test_mutate_genome_deterministic_and_new_object():
    cfg = GenomeConfig(mutation_rate=0.5)
    g = Genome(np.linspace(0, 1, 16))
    a = mutate_genome(g, np.random.default_rng(1), cfg)
    b = mutate_genome(g, np.random.default_rng(1), cfg)
    assert a == b
    assert a.gene_count == g.gene_count
    assert a != g  # 变异率 0.5 × 16 基因，几乎必然发生变异


def test_mutate_genome_zero_rate_identical_copy():
    cfg = GenomeConfig(mutation_rate=0.0)
    g = Genome(np.linspace(0, 1, 16))
    out = mutate_genome(g, np.random.default_rng(0), cfg)
    assert out == g
    assert out is not g  # 仍是新对象


def test_mutate_genome_respects_bounds():
    cfg = GenomeConfig(mutation_rate=1.0, mutation_sigma=10.0)
    g = Genome(np.zeros(16))
    out = mutate_genome(g, np.random.default_rng(0), cfg)
    assert np.all(out.genes >= cfg.gene_min)
    assert np.all(out.genes <= cfg.gene_max)