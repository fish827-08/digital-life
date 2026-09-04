"""Genetics 测试：解码契约、变异、交叉的纯函数性质。"""
from __future__ import annotations

import numpy as np
import pytest

from core import genetics
from core.genetics import TRAIT_TABLE, crossover, decode, mutate
from simulation.config import GenomeConfig


def test_trait_table_contract():
    """结构契约固化：第一阶段必须且只能有这四个性状。"""
    assert [t.name for t in TRAIT_TABLE] == [
        "move_prob",
        "metabolism_mult",
        "repro_fraction",
        "life_span",
    ]


def test_decode_zero_genes_give_lo_bounds():
    genes = np.zeros(8)
    p = decode(genes)
    assert p["move_prob"] == 0.0
    assert p["metabolism_mult"] == 0.5
    assert p["repro_fraction"] == 0.25
    assert p["life_span"] == 200.0


def test_decode_one_genes_give_hi_bounds():
    genes = np.ones(8)
    p = decode(genes)
    assert p["move_prob"] == 1.0
    assert p["metabolism_mult"] == 2.0
    assert p["repro_fraction"] == 0.9
    assert p["life_span"] == 4000.0


def test_decode_is_linear_midpoint():
    genes = np.full(8, 0.5)
    p = decode(genes)
    assert p["move_prob"] == pytest.approx(0.5)
    assert p["metabolism_mult"] == pytest.approx(1.25)
    assert p["repro_fraction"] == pytest.approx(0.575)


def test_decode_returns_only_declared_traits():
    genes = np.linspace(0, 1, 16)
    assert set(decode(genes).keys()) == {t.name for t in TRAIT_TABLE}


def test_decode_rejects_short_genome():
    with pytest.raises(ValueError):
        decode(np.zeros(3))  # 最大基因索引是 3，长度 3 无法覆盖
    assert set(decode(np.zeros(4)).keys()) == {t.name for t in TRAIT_TABLE}  # 长度 4 恰好合法


def test_mutate_zero_rate_is_pure_copy():
    rng = np.random.default_rng(0)
    cfg = GenomeConfig(mutation_rate=0.0)
    genes = np.linspace(0, 1, 16)
    out = mutate(genes, rng, cfg)
    assert np.array_equal(out, genes)
    assert out is not genes  # 返回新数组


def test_mutate_does_not_modify_input():
    rng = np.random.default_rng(0)
    cfg = GenomeConfig(mutation_rate=1.0)
    genes = np.linspace(0, 1, 16)
    snapshot = genes.copy()
    mutate(genes, rng, cfg)
    assert np.array_equal(genes, snapshot)


def test_mutate_clips_to_bounds():
    rng = np.random.default_rng(0)
    cfg = GenomeConfig(mutation_rate=1.0, mutation_sigma=10.0)  # 大扰动验证截断
    genes = np.zeros(16)
    out = mutate(genes, rng, cfg)
    assert np.all(out >= cfg.gene_min)
    assert np.all(out <= cfg.gene_max)


def test_mutate_deterministic():
    genes = np.linspace(0, 1, 16)
    cfg = GenomeConfig(mutation_rate=0.2)
    out1 = mutate(genes, np.random.default_rng(7), cfg)
    out2 = mutate(genes, np.random.default_rng(7), cfg)
    assert np.array_equal(out1, out2)


def test_crossover_zero_rate_is_copy():
    cfg = GenomeConfig(crossover_rate=0.0)
    a = np.linspace(0, 1, 8)
    b = np.linspace(1, 0, 8)
    c1, c2 = crossover(a, b, np.random.default_rng(0), cfg)
    assert np.array_equal(c1, a) and np.array_equal(c2, b)


def test_crossover_preserves_gene_multiset():
    """交叉不改写基因"内容集合"：两个子代拼起来 == 两个亲本拼起来。"""
    cfg = GenomeConfig(crossover_rate=1.0)
    a = np.linspace(0, 1, 8)
    b = np.linspace(2, 3, 8)
    c1, c2 = crossover(a, b, np.random.default_rng(3), cfg)
    assert np.array_equal(np.sort(np.concatenate([c1, c2])), np.sort(np.concatenate([a, b])))
    assert c1.size == a.size and c2.size == a.size


def test_crossover_deterministic():
    cfg = GenomeConfig(crossover_rate=1.0)
    a = np.linspace(0, 1, 8)
    b = np.linspace(9, 1, 8)
    r1 = crossover(a, b, np.random.default_rng(5), cfg)
    r2 = crossover(a, b, np.random.default_rng(5), cfg)
    assert np.array_equal(r1[0], r2[0]) and np.array_equal(r1[1], r2[1])


def test_crossover_uneven_length_rejected():
    cfg = GenomeConfig()
    with pytest.raises(ValueError):
        crossover(np.zeros(4), np.zeros(8), np.random.default_rng(0), cfg)