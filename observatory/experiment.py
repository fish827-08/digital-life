"""ExperimentRunner：确定性实验调度与结果聚合。

实验固定契约：
- 每个实验 = (ExperimentSpec, 派生 seed)。种子由
  SeedSequence([base_seed, group_id, seed_index]) 确定性派生 →
  同一命令行参数必然复现同一批结果（deterministic experiment support）。
- 运行语义：engine 每 tick 推进，observer 每 tick 观察；停止条件为
  三者任一：达到 max_generations（世代达标）/ 引擎自身结束（跑满
  tick 或灭绝防护）/ 达到 max_ticks 硬上限（防失控）。
- runner 不引入任何"适应度"概念：演化方向完全由既有生命规则涌现。

本模块不碰统计口径（见 statistics.py），只负责"跑哪些实验、按什么
顺序、如何汇总"。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

from observatory.observer import EvolutionObserver, GenerationSample
from observatory.statistics import TRAIT_ORDER
from simulation.config import SimConfig
from simulation.engine import SimulationEngine
from simulation.vecengine import VecEngine

# 硬上限：单个实验最长 tick 数（64x64 下约 2 小时；防参数失误失控）
DEFAULT_MAX_TICKS = 1_200_000


@dataclass(frozen=True)
class ExperimentSpec:
    """一份实验规格（可复现的最小单位）。"""

    name: str
    group: str  # baseline / resource_pressure / resource_distribution / mutation_rate / repeated_seeds
    description: str
    overrides: dict = field(default_factory=dict)  # SimConfig 覆盖（如 {"resources": {...}}）
    max_generations: int = 10_000
    max_ticks: int = DEFAULT_MAX_TICKS
    seed_index: int = 0  # 组内序号（repeated seeds 用）

    @property
    def group_id(self) -> int:
        return _GROUP_IDS[self.group]


# 组 → 稳定整数 id（种子派生用；新增组需登记）
_GROUP_IDS = {
    "baseline": 0,
    "resource_pressure": 1,
    "resource_distribution": 2,
    "mutation_rate": 3,
    "repeated_seeds": 4,
}


def derive_seed(base_seed: int, group_id: int, seed_index: int) -> int:
    """确定性派生一个实验种子（与运行次数无关）。"""
    return int(np.random.SeedSequence([base_seed, group_id, seed_index]).generate_state(1)[0])


@dataclass(frozen=True)
class ExperimentRun:
    """一个具体运行实例 = spec + 派生种子。"""

    spec: ExperimentSpec
    seed: int


@dataclass
class ExperimentResult:
    """一次运行的完整结果（可持久化）。"""

    run: ExperimentRun
    config: SimConfig
    finished_normally: bool  # True = 世代达标
    ended_reason: str  # "generations_reached" / "engine_finished" / "max_ticks"
    extinct: bool
    total_ticks: int
    final_population: int
    duration_s: float
    samples: list[GenerationSample] = field(default_factory=list)
    totals: dict = field(default_factory=dict)
    summary: dict = field(default_factory=dict)


# ---- 预置实验矩阵（Stage 2 要求的 5 类） ---------------------------------


def build_plan(
    base_seed: int = 42,
    max_generations: int = 1_000,
    short_generations: int = 250,
    repeated_seed_count: int = 3,
    repeated_generations: int = 250,
    baseline_max_ticks: int | None = None,
) -> list[ExperimentRun]:
    """构建完整实验计划。

    规模语义（世代深度由生态物理决定，实测 ~850-1500 tick/代，随
    种群收缩而变慢）：
    - baseline 是唯一的长程实验。默认精简约 1,000 代（64x64 下约
      40-45 分钟），用于验证"跨千代的选择性变化"；其 tick 硬上限
      由 max_generations 自动推导（~1,800 tick/代 × 安全系数），
      也可用 baseline_max_ticks 显式覆盖；
    - 完整能力档（10,000 代 ≈ 90-180 万 tick/代 × 1 万 ≈ 数小时级）
      通过 max_generations=10_000 显式启用（机制本就支持，默认不开
      以免数小时级排队）；
    - 其余对照实验跑 short_generations 代（默认 250 代，
      快速对比不同选择压下的遗传漂变方向与幅度）；
    - repeated_seeds 组同配置多种子跑 repeated_generations 代，
      用于跨 seed 方差分析。
    """
    # baseline 长程 tick 预算：按世代数与实测世代速率自动推导，
    # 保证默认 1,000 代不再被 1.2M 上限截断（避免"达标但没跑完"）。
    if baseline_max_ticks is None:
        baseline_max_ticks = max(DEFAULT_MAX_TICKS, int(max_generations * 1_800))
    specs: list[ExperimentSpec] = [
        # Baseline：默认生态（对照组，完整长程）
        ExperimentSpec(
            "baseline", "baseline",
            "默认生态参数（对照组）：均匀资源、默认变异率", {},
            max_generations=max_generations,
            max_ticks=baseline_max_ticks,
        ),
        # Resource Pressure：资源再生压力（短程对照）
        ExperimentSpec(
            "pressure_low", "resource_pressure",
            "资源再生率降至 1/4（每周期的食物供给收紧）",
            {"resources": {"regrowth_rate": 0.005}},
            max_generations=short_generations,
        ),
        ExperimentSpec(
            "pressure_critical", "resource_pressure",
            "资源再生率近零（慢性饥饿，检验灭绝动力学）",
            {"resources": {"regrowth_rate": 0.001}},
            max_generations=short_generations,
        ),
        # Resource Distribution：资源分布形态（短程对照）
        ExperimentSpec(
            "dist_uniform_sparse", "resource_distribution",
            "初始资源稀疏但均匀（总供给偏紧）",
            {"resources": {"initial_fill": 0.08}},
            max_generations=short_generations,
        ),
        ExperimentSpec(
            "dist_uniform_rich", "resource_distribution",
            "初始资源富饶且均匀",
            {"resources": {"initial_fill": 0.8}},
            max_generations=short_generations,
        ),
        ExperimentSpec(
            "dist_patchy", "resource_distribution",
            "块状异质资源（富饶/贫瘠斑块）",
            {"resources": {"initial_fill": 0.4, "patchiness": 0.8}},
            max_generations=short_generations,
        ),
        # Mutation Rate：变异强度（短程对照）
        ExperimentSpec(
            "mutation_low", "mutation_rate",
            "变异率降为默认 1/10",
            {"genome": {"mutation_rate": 0.005}},
            max_generations=short_generations,
        ),
        ExperimentSpec(
            "mutation_high", "mutation_rate",
            "变异率升为默认 6 倍",
            {"genome": {"mutation_rate": 0.3}},
            max_generations=short_generations,
        ),
    ]
    runs = [ExperimentRun(spec=spec, seed=derive_seed(base_seed, spec.group_id, spec.seed_index)) for spec in specs]
    # Repeated Seeds：同 baseline 配置多种子（跨 seed 方差分析）
    for i in range(repeated_seed_count):
        spec = ExperimentSpec(
            f"repeated_seed_{i + 1}", "repeated_seeds",
            f"baseline 配置 × 种子变体 {i + 1}（跨 seed 可重复性）", {},
            max_generations=repeated_generations,
            seed_index=i,
        )
        runs.append(ExperimentRun(spec=spec, seed=derive_seed(base_seed, spec.group_id, i)))
    return runs


# ---- Runner ---------------------------------------------------------------


class ExperimentRunner:
    """按计划跑实验，产出可持久化的 ExperimentResult。"""

    def __init__(
        self,
        base_seed: int = 42,
        world_size: tuple[int, int] = (64, 64),
        tick_interval: int = 100,
        use_vec: bool = False,
    ) -> None:
        self.base_seed = base_seed
        self.world_size = world_size
        self.tick_interval = tick_interval
        self.use_vec = use_vec  # True = 数组化引擎（速度优先，统计等价）

    # ---- 计划 --------------------------------------------------------

    def plan(self, **kwargs) -> list[ExperimentRun]:
        return build_plan(base_seed=self.base_seed, **kwargs)

    # ---- 单跑 ---------------------------------------------------------

    def run_single(self, run: ExperimentRun) -> ExperimentResult:
        cfg = SimConfig(
            seed=run.seed,
            world={"width": self.world_size[0], "height": self.world_size[1]},
            simulation={
                "ticks": max(run.spec.max_ticks, 1),
                "stop_on_extinction": True,
                # 有界历史：观察者从 per-tick 统计累积窗口，不依赖全量
                # 历史 → 百万 tick 级长程实验内存有上界（避免 OOM）。
                "history_limit": 4_096,
            },
            **run.spec.overrides,
        )
        engine_cls = VecEngine if self.use_vec else SimulationEngine
        engine = engine_cls(cfg)
        observer = EvolutionObserver(engine, tick_interval=self.tick_interval)

        target = run.spec.max_generations
        cap = run.spec.max_ticks
        t0 = time.perf_counter()
        while (
            not engine.finished
            and engine.tick < cap
            and engine.population.max_generation < target
        ):
            stats = engine.step()
            observer.observe(stats)

        duration = time.perf_counter() - t0
        if engine.population.max_generation >= target:
            ended_reason = "generations_reached"
            finished_normally = True
        elif engine.finished:
            ended_reason = "engine_finished"
            finished_normally = False
        else:
            ended_reason = "max_ticks"
            finished_normally = False

        return ExperimentResult(
            run=run,
            config=cfg,
            finished_normally=finished_normally,
            ended_reason=ended_reason,
            extinct=engine.extinct,
            total_ticks=engine.tick,
            final_population=engine.population.alive_count(),
            duration_s=duration,
            samples=observer.samples,
            totals=_totals(engine),
            summary=_summarize(run, engine, observer),
        )

    # ---- 批量 -----------------------------------------------------------

    def run_plan(
        self,
        runs: list[ExperimentRun],
        only: Optional[list[str]] = None,
        quiet: bool = False,
        out_dir: str | Path | None = None,
    ) -> dict[str, ExperimentResult]:
        """批量运行；out_dir 给定时，每个实验完成后立即落盘（可中途停止不丢结果）。"""
        results: dict[str, ExperimentResult] = {}
        selected = [r for r in runs if only is None or r.spec.name in only]
        for i, run in enumerate(selected, 1):
            if not quiet:
                print(
                    f"[{i}/{len(selected)}] {run.spec.name} "
                    f"(seed={run.seed}, {run.spec.description})",
                    flush=True,
                )
            res = self.run_single(run)
            results[run.spec.name] = res
            if out_dir is not None:
                # 即时持久化：跑到一半就停也不丢已完成实验
                from persistence.io import save_experiment

                save_experiment(res, Path(out_dir) / run.spec.name)
            if not quiet:
                status = "达标" if res.finished_normally else res.ended_reason
                print(
                    f"     -> 世代={res.summary.get('generations_reached', 0)}, "
                    f"tick={res.total_ticks}, 种群={res.final_population}, "
                    f"状态={status}, 耗时={res.duration_s:.0f}s",
                    flush=True,
                )
        return results


# ---- 结果加工 --------------------------------------------------------------


def _totals(engine: SimulationEngine) -> dict:
    return {
        "total_born": engine.total_born,
        "total_died": engine.total_died,
        "deaths_by_cause": {
            (k.value if hasattr(k, "value") else str(k)): v
            for k, v in engine.death_cause_totals().items()
        },
        "total_energy": engine.population.total_energy(),
        "total_resource": engine.world.total_resource(),
    }


def _summarize(run: ExperimentRun, engine: SimulationEngine, observer: EvolutionObserver) -> dict:
    """观测点首/末/中 + 关键趋势（只聚合，不做价值判断）。"""
    samples = observer.samples
    if not samples:
        return {"generations_reached": engine.population.max_generation}
    first, last = samples[0], samples[-1]
    mid = samples[len(samples) // 2]
    s_f, s_m, s_l = first.stats, mid.stats, last.stats
    trait_drift = {
        t: {
            "start": s_f.trait_means[t],
            "mid": s_m.trait_means[t],
            "end": s_l.trait_means[t],
            "drift": s_l.trait_means[t] - s_f.trait_means[t],
        }
        for t in TRAIT_ORDER
    }
    return {
        "generations_reached": last.generation,
        "first_tick": first.tick,
        "last_tick": last.tick,
        "final_population": last.stats.population,
        "population_series": [s_f.population, s_m.population, s_l.population],
        "diversity": {
            "start": s_f.genome_diversity,
            "mid": s_m.genome_diversity,
            "end": s_l.genome_diversity,
            "drift": s_l.genome_diversity - s_f.genome_diversity,
        },
        "mean_life_span": {
            "start": s_f.trait_means["life_span"],
            "end": s_l.trait_means["life_span"],
        },
        "trait_drift": trait_drift,
        "final_birth_rate": last.birth_rate,
        "final_death_rate": last.death_rate,
    }