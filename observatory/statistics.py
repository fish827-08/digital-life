"""EvolutionStatistics：观测层纯函数统计聚合。

职责：
- 输入：当前存活个体集合（Iterable[Organism]）；
- 输出：一个"观测点"的全部统计量（trait 分布 / 基因组多样性 / 谱系）。
  无副作用、无内部状态 → 同一输入必然同一输出，可复现、可对比。

本模块只"计算"，不做任何解释/推断（解释交给 ExperimentRunner 的摘要）。

统计口径（在导出列名上显式声明）：
- trait 分布：均值 / 标准差（按出生时的基因解码表现型）
- 基因组多样性：平均每位点离散杂合度（Simpson 型，0=单态，1=最大）
- 谱系：世代号分布（存活个体）、世代号中位数/均值
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass

import numpy as np

from core.genetics import TRAIT_TABLE
from core.organism import Organism

# trait 顺序与核心契约保持一致（避免两处硬编码）
TRAIT_ORDER: tuple[str, ...] = tuple(t.name for t in TRAIT_TABLE)

# 基因组多样性：基因值离散化箱数（[gene_min, gene_max) 均分）
_HET_BINS = 16
# 唯一基因型判定：离散化精度（小数点后位数）
_UQ_DECIMALS = 3
# 世代直方图的固定对数桶上界（世代号 → "0-9","10-99",...）
_GEN_BIN_EDGES = (0, 1, 10, 100, 1000, 10_000, 100_000)


@dataclass(frozen=True)
class GenerationStats:
    """一个观测点的聚合统计（全部字段 JSON 安全）。"""

    population: int
    mean_age: float
    mean_energy: float
    max_generation: int
    median_generation: float
    mean_generation: float
    generation_histogram: dict[str, int]  # 固定对数桶 {"0-0": n, "1-9": n, ...}
    trait_means: dict[str, float]
    trait_stds: dict[str, float]
    genome_diversity: float  # 平均每位点杂合度
    unique_genotypes: int  # 量化后不同基因型个数
    unique_genotype_ratio: float

    def to_dict(self) -> dict:
        return asdict(self)


def _empty_stats() -> GenerationStats:
    return GenerationStats(
        population=0,
        mean_age=0.0,
        mean_energy=0.0,
        max_generation=-1,
        median_generation=0.0,
        mean_generation=0.0,
        generation_histogram={},
        trait_means={t: 0.0 for t in TRAIT_ORDER},
        trait_stds={t: 0.0 for t in TRAIT_ORDER},
        genome_diversity=0.0,
        unique_genotypes=0,
        unique_genotype_ratio=0.0,
    )


def generation_statistics(organisms: Iterable[Organism]) -> GenerationStats:
    """从存活个体集合聚合一个观测点。空种群返回全零（合法观测点）。"""
    orgs = list(organisms)
    n = len(orgs)
    if n == 0:
        return _empty_stats()

    ages = np.fromiter((o.lifecycle.age for o in orgs), dtype=np.float64, count=n)
    energies = np.fromiter((o.energy for o in orgs), dtype=np.float64, count=n)
    gens = np.fromiter((o.generation for o in orgs), dtype=np.int64, count=n)
    genes = np.stack([o.genome.genes for o in orgs])  # (n, gene_count)

    # ---- trait 分布（表现型，来自基因解码的缓存字典） ----
    traits = np.stack(
        [[o.phenotype[t] for t in TRAIT_ORDER] for o in orgs]
    )  # (n, n_traits)

    # ---- 基因组多样性：每位点离散化 → Simpson 杂合度 ----
    binned = np.floor(genes * _HET_BINS).clip(0, _HET_BINS - 1).astype(np.int64)
    het_per_locus = []
    for locus in range(genes.shape[1]):
        counts = np.bincount(binned[:, locus], minlength=_HET_BINS).astype(np.float64)
        probs = counts / n
        het_per_locus.append(1.0 - float((probs**2).sum()))
    diversity = float(np.mean(het_per_locus)) if het_per_locus else 0.0

    # ---- 唯一基因型 ----
    unique_rows = np.unique(np.round(genes, _UQ_DECIMALS), axis=0)
    unique_count = len(unique_rows)

    # ---- 世代直方图（对数桶） ----
    edges = np.array(_GEN_BIN_EDGES, dtype=np.int64)
    indices = np.clip(np.searchsorted(edges, gens, side="right") - 1, 0, len(edges) - 2)
    hist = {}
    for i in range(len(edges) - 1):
        lo, hi = int(edges[i]), int(edges[i + 1]) - 1
        label = f"{lo}-{hi}"
        hist[label] = int((indices == i).sum())

    return GenerationStats(
        population=n,
        mean_age=float(ages.mean()),
        mean_energy=float(energies.mean()),
        max_generation=int(gens.max()),
        median_generation=float(np.median(gens)),
        mean_generation=float(gens.mean()),
        generation_histogram=hist,
        trait_means={t: float(traits[:, i].mean()) for i, t in enumerate(TRAIT_ORDER)},
        trait_stds={t: float(traits[:, i].std()) for i, t in enumerate(TRAIT_ORDER)},
        genome_diversity=diversity,
        unique_genotypes=int(unique_count),
        unique_genotype_ratio=float(unique_count / n),
    )