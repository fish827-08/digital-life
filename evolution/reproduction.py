"""Reproduction：繁殖规则 —— 子代基因组与出生能量。

设计原因：
- 繁殖"怎么产生子代"集中于此。v1 采用无性繁殖（二分裂）：
  子代基因组 = 亲代基因 + 变异，出生能量 = 亲代当前能量的一半；
- 有性繁殖（crossover）在基因层面已具备（core.genetics.crossover），
  留待种群出现配偶 / 通信机制时再接入（原则 9）；
- 本模块只产出"子代的定义"，不直接修改亲代能量 —— 由调用方
  （Population）执行能量扣减，保证副作用单一（原则 6）。
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from core import genetics
from core.genome import Genome
from core.organism import Organism
from simulation.config import GenomeConfig


@dataclass(frozen=True)
class Offspring:
    """子代定义：基因组 + 出生携带能量。"""

    genome: Genome
    energy: float


def create_offspring(
    parent: Organism, rng: np.random.Generator, config: GenomeConfig
) -> Offspring:
    """无性繁殖：子代基因组 = 亲代基因 + 变异；能量 = 亲代当前能量的一半。"""
    child_genes = genetics.mutate(parent.genome.genes, rng, config)
    return Offspring(genome=Genome(child_genes), energy=parent.energy / 2.0)