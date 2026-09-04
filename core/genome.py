"""Genome：定长连续基因链（基因型）。纯数据容器。

表示：一条 NumPy float64 一维数组（原理 7：为百万级种群/向量化运算留底子）。

职责边界（原则 6：避免逻辑写死在单一类）：
- 本类只承担"表示、工厂、复制、比较"；
- 所有遗传运算（变异 / 交叉 / 解码）都放在 core.genetics.py 中，
  保持"数据"与"规则"分离，二者可独立替换。
"""
from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from simulation.config import GenomeConfig


class Genome:
    """定长连续基因链（基因型）。"""

    __slots__ = ("genes",)

    def __init__(self, genes: NDArray[np.float64]) -> None:
        if genes.ndim != 1:
            raise ValueError(f"基因链必须是一维数组，实际 ndim={genes.ndim}")
        self.genes = genes.astype(np.float64, copy=False)

    # ---- 工厂 ----------------------------------------------------------

    @classmethod
    def random(
        cls, config: GenomeConfig, rng: np.random.Generator
    ) -> "Genome":
        """用 rng 在 [gene_min, gene_max) 均匀采样生成随机基因组（初代用）。"""
        values = rng.uniform(config.gene_min, config.gene_max, size=config.gene_count)
        return cls(values)

    # ---- 属性 ----------------------------------------------------------

    @property
    def gene_count(self) -> int:
        return self.genes.size

    # ---- 复制与比较 ----------------------------------------------------

    def copy(self) -> "Genome":
        return Genome(self.genes.copy())

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Genome):
            return NotImplemented
        return self.genes.shape == other.genes.shape and bool(
            np.array_equal(self.genes, other.genes)
        )

    def __repr__(self) -> str:
        return f"Genome(n={self.gene_count}, mean={self.genes.mean():.3f})"