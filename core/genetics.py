"""Genetics：基因型 → 表现型的解码契约，以及变异 / 交叉纯函数。

设计要点：
- 这里声明"性状如何从基因解码"（结构契约），是可替换单元：
  替换基因表达方式 = 换掉本模块的 decode，其余模块不感知（原则 4）。
- 所有函数都是纯函数：显式传入 rng 与配置，不持有全局状态
  （确定性 = 可复现的前提，原则 8）。
- TRAIT_TABLE 之外的基因 = 中立基因：不被解码使用，仍参与变异与
  重组，构成"中性漂移区"，为将来复杂性状保留进化底物。
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from simulation.config import GenomeConfig


@dataclass(frozen=True)
class Trait:
    """单个性状的解码声明：基因位点 + 线性映射区间。"""

    name: str
    gene_index: int
    lo: float
    hi: float

    def decode(self, gene: float) -> float:
        """把 [0,1] 基因值线性映射到性状区间 [lo, hi]。"""
        return self.lo + gene * (self.hi - self.lo)


# 第一阶段性状契约（结构契约，非数值参数——数值一律进 config）
#   move_prob       : 每 tick 移动概率
#   metabolism_mult : 代谢倍率（乘以 config 的 base_metabolism）
#   repro_fraction  : 繁殖能量阈值 = 该比例 × max_energy
#   life_span       : 寿命（tick 数）
TRAIT_TABLE: tuple[Trait, ...] = (
    Trait("move_prob", 0, 0.0, 1.0),
    Trait("metabolism_mult", 1, 0.5, 2.0),
    Trait("repro_fraction", 2, 0.25, 0.9),
    Trait("life_span", 3, 200.0, 4000.0),
)


def decode(genes: NDArray[np.float64]) -> dict[str, float]:
    """基因型 → 表现型：按 TRAIT_TABLE 解码出全部性状值。"""
    if genes.size <= max(t.gene_index for t in TRAIT_TABLE):
        raise ValueError("基因链长度不足，无法解码全部性状")
    return {t.name: t.decode(float(genes[t.gene_index])) for t in TRAIT_TABLE}


def mutate(
    genes: NDArray[np.float64],
    rng: np.random.Generator,
    config: GenomeConfig,
) -> NDArray[np.float64]:
    """基础随机变异：每个基因以 mutation_rate 概率被高斯扰动。

    - 扰动幅度：mutation_sigma × 基因区间宽度（相对幅度）
    - 结果截断到 [gene_min, gene_max]
    - 返回新数组；不改动入参（纯函数）
    """
    sigma = config.mutation_sigma * (config.gene_max - config.gene_min)
    result = genes.copy()
    mask = rng.random(result.size) < config.mutation_rate
    if mask.any():
        noise = rng.normal(0.0, sigma, size=result.size)
        result[mask] += noise[mask]
        result = np.clip(result, config.gene_min, config.gene_max)
    return result


def crossover(
    a: NDArray[np.float64],
    b: NDArray[np.float64],
    rng: np.random.Generator,
    config: GenomeConfig,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """单点交叉：以 crossover_rate 概率在随机位点切开互换，否则原样复制。

    返回两条等长重组后代。
    """
    if a.size != b.size:
        raise ValueError("交叉需要等长基因链")
    if rng.random() >= config.crossover_rate:
        return a.copy(), b.copy()
    cut = int(rng.integers(1, a.size))  # 切点两侧均有基因
    return (
        np.concatenate([a[:cut], b[cut:]]),
        np.concatenate([b[:cut], a[cut:]]),
    )