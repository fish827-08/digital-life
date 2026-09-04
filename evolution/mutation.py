"""Mutation：变异策略 —— 把 core.genetics 的基因规则应用到 Genome 对象。

设计原因：
- 基因层面的"怎么变异"（高斯扰动 / 截断）是 core.genetics 的纯函数；
  这里做"策略化"包装：以 Genome 为输入输出，是演化层唯一的变异入口。
  未来换自适应变异率、定向变异等策略时只改本模块（原则 4/6）。
"""
from __future__ import annotations

import numpy as np

from core import genetics
from core.genome import Genome
from simulation.config import GenomeConfig


def mutate_genome(
    genome: Genome, rng: np.random.Generator, config: GenomeConfig
) -> Genome:
    """对基因链施加变异，返回新 Genome（纯函数语义：不改原对象）。"""
    return Genome(genetics.mutate(genome.genes, rng, config))