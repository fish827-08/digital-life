"""Genome 容器测试：表示、工厂、复制、比较。"""
from __future__ import annotations

import numpy as np
import pytest

from core.genome import Genome
from simulation.config import GenomeConfig

CFG = GenomeConfig()


def test_random_genome_length_and_range():
    rng = np.random.default_rng(1)
    g = Genome.random(CFG, rng)
    assert g.gene_count == CFG.gene_count
    assert g.genes.shape == (CFG.gene_count,)
    assert np.all(g.genes >= CFG.gene_min)
    assert np.all(g.genes < CFG.gene_max)


def test_random_is_deterministic_with_same_seed():
    g1 = Genome.random(CFG, np.random.default_rng(42))
    g2 = Genome.random(CFG, np.random.default_rng(42))
    assert g1 == g2
    g3 = Genome.random(CFG, np.random.default_rng(43))
    assert g1 != g3


def test_copy_is_independent():
    g = Genome(np.array([0.1, 0.2, 0.3]))
    c = g.copy()
    c.genes[0] = 0.9
    assert g.genes[0] == 0.1  # 原对象不受影响


def test_equality():
    g = Genome(np.array([0.1, 0.2]))
    assert g == Genome(np.array([0.1, 0.2]))
    assert g != Genome(np.array([0.1, 0.3]))
    assert g != Genome(np.array([0.1]))  # 长度不同


def test_equality_with_other_type_is_false():
    g = Genome(np.array([0.1]))
    assert not (g == np.array([0.1]))  # NotImplemented → False


def test_invalid_ndim_rejected():
    with pytest.raises(ValueError):
        Genome(np.ones((2, 2)))  # 二维数组不是合法基因链