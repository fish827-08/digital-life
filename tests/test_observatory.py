"""Stage 2 — Evolution Observatory 测试。

覆盖：
- 观测元数据（generation / parent_id 血缘传播，不改行为）
- EvolutionStatistics 纯函数聚合（trait 分布 / 基因组多样性 / 世代统计）
- EvolutionObserver 世代采样（含窗口出生/死亡率）
- ExperimentRunner 确定性 / 结束语义 / 实验矩阵
- 结果持久化 IO 往返（JSON + CSV）
"""
from __future__ import annotations

import json

import numpy as np
import pytest

from core.genome import Genome
from core.organism import Organism
from evolution.population import Population
from observatory.experiment import (
    DEFAULT_MAX_TICKS,
    ExperimentResult,
    ExperimentRun,
    ExperimentSpec,
    ExperimentRunner,
    build_plan,
    derive_seed,
)
from observatory.observer import EvolutionObserver
from observatory.statistics import TRAIT_ORDER, GenerationStats, generation_statistics
from persistence.io import (
    load_generations,
    load_manifest,
    save_experiment,
    save_survey,
    save_survey_markdown,
)
from simulation.config import SimConfig
from simulation.engine import SimulationEngine

# ---- 观测元数据 -------------------------------------------------------------


def _sim_config(**kw) -> SimConfig:
    base = dict(
        seed=7,
        world={"width": 64, "height": 64},
        simulation={"ticks": 5_000, "stop_on_extinction": True},
    )
    base.update(kw)
    return SimConfig(**base)


def test_organism_generation_validation() -> None:
    cfg = SimConfig()
    g = Genome.random(cfg.genome, np.random.default_rng(1))
    with pytest.raises(ValueError):
        Organism(
            organism_id=1, x=0, y=0, genome=g, config=cfg.organisms, generation=-1
        )


def test_organism_generation_defaults() -> None:
    cfg = SimConfig()
    g = Genome.random(cfg.genome, np.random.default_rng(1))
    o = Organism(organism_id=1, x=0, y=0, genome=g, config=cfg.organisms)
    assert o.generation == 0
    assert o.parent_id is None


def test_population_lineage_propagation() -> None:
    """存活个体间血缘可查：child.generation == parent.generation + 1。"""
    cfg = _sim_config()
    eng = SimulationEngine(cfg)
    assert eng.population.max_generation == 0
    eng.run(3_000)
    alive = {o.organism_id: o for o in eng.population.organisms()}
    pairs = [
        (child, alive[child.parent_id])
        for child in alive.values()
        if child.parent_id is not None and child.parent_id in alive
    ]
    assert pairs, "应存在亲代仍存活的活体父子对（血缘连续可查）"
    for child, parent in pairs:
        assert child.generation == parent.generation + 1
    assert eng.population.max_generation == max(
        o.generation for o in alive.values()
    )


# ---- EvolutionStatistics ----------------------------------------------------


def test_statistics_empty_is_all_zero() -> None:
    s = generation_statistics([])
    assert s.population == 0
    assert s.max_generation == -1
    assert s.trait_means == {t: 0.0 for t in TRAIT_ORDER}
    assert s.genome_diversity == 0.0


def test_statistics_single_organism() -> None:
    cfg = SimConfig()
    rng = np.random.default_rng(3)
    g = Genome.random(cfg.genome, rng)
    o = Organism(
        organism_id=1, x=0, y=0, genome=g, config=cfg.organisms, generation=5
    )
    s = generation_statistics([o])
    assert s.population == 1
    assert s.max_generation == 5
    for t in TRAIT_ORDER:
        assert s.trait_means[t] == pytest.approx(o.phenotype[t])
        assert s.trait_stds[t] == pytest.approx(0.0)
    assert s.unique_genotypes == 1
    assert s.genome_diversity == pytest.approx(0.0)  # 单个体 → 每位点单态


def test_statistics_deterministic() -> None:
    """同一输入集合必然产出完全相同统计（统计口径可复现）。"""
    cfg = SimConfig()
    rng = np.random.default_rng(5)
    orgs = [
        Organism(
            organism_id=i,
            x=0,
            y=0,
            genome=Genome.random(cfg.genome, rng),
            config=cfg.organisms,
            generation=i % 3,
        )
        for i in range(30)
    ]
    s1 = generation_statistics(orgs)
    s2 = generation_statistics(orgs)
    assert s1 == s2


def test_statistics_diversity_bounds_and_trend() -> None:
    """克隆群体多样性=0；多样化后多样性>0；且 ∈ [0, 1]。"""
    cfg = SimConfig()
    base = Genome.random(cfg.genome, np.random.default_rng(1))
    clones = [
        Organism(
            organism_id=i, x=0, y=0, genome=base, config=cfg.organisms, generation=0
        )
        for i in range(10)
    ]
    assert generation_statistics(clones).genome_diversity == pytest.approx(0.0)
    diverged = [
        Organism(
            organism_id=i,
            x=0,
            y=0,
            genome=Genome.random(cfg.genome, np.random.default_rng(i)),
            config=cfg.organisms,
            generation=0,
        )
        for i in range(10)
    ]
    d = generation_statistics(diverged).genome_diversity
    assert 0.0 < d <= 1.0


def test_statistics_generation_histogram_and_median() -> None:
    cfg = SimConfig()
    rng = np.random.default_rng(9)
    generation = list(range(0, 20)) + [100]
    orgs = [
        Organism(
            organism_id=i,
            x=0,
            y=0,
            genome=Genome.random(cfg.genome, rng),
            config=cfg.organisms,
            generation=g,
        )
        for i, g in enumerate(generation)
    ]
    s = generation_statistics(orgs)
    assert s.max_generation == 100
    assert s.median_generation == pytest.approx(10.0)  # 21 个值的正中 = 第 11 个 = 10
    assert sum(s.generation_histogram.values()) == len(orgs)


# ---- EvolutionObserver ------------------------------------------------------


def test_observer_samples_when_generation_advances() -> None:
    cfg = _sim_config(simulation={"ticks": 10_000, "stop_on_extinction": True})
    eng = SimulationEngine(cfg)
    obs = EvolutionObserver(eng, tick_interval=10_000)  # 兜底形同虚设 → 仅世代触发
    for _ in range(10_000):
        eng.step()
        obs.observe()
    assert len(obs.samples) >= 2, "世代推进时应至少采样两次"
    ticks = [s.tick for s in obs.samples]
    assert ticks == sorted(ticks)
    gens = [s.generation for s in obs.samples]
    assert gens == sorted(gens)


def test_observer_tick_interval_fallback() -> None:
    cfg = _sim_config(simulation={"ticks": 30, "stop_on_extinction": False})
    eng = SimulationEngine(cfg)
    obs = EvolutionObserver(eng, tick_interval=10)
    for _ in range(30):
        obs.observe(eng.step())
    assert len(obs.samples) >= 3  # 10/20/30 三个兜底点
    for s in obs.samples:
        assert s.span_ticks >= 1
        assert s.birth_rate >= 0.0 and s.death_rate >= 0.0


def test_observer_rejects_negative_interval() -> None:
    cfg = _sim_config()
    eng = SimulationEngine(cfg)
    with pytest.raises(ValueError):
        EvolutionObserver(eng, tick_interval=-1)


def test_engine_bounded_history_totals() -> None:
    """history_limit>0：历史裁剪但总量/死因汇总完整，且演化逐点复现。"""

    def run(limit: int) -> SimulationEngine:
        cfg = _sim_config(
            simulation={
                "ticks": 3_000,
                "stop_on_extinction": False,
                "history_limit": limit,
            }
        )
        eng = SimulationEngine(cfg)
        eng.run()
        return eng

    unbounded = run(0)
    bounded = run(200)
    assert len(bounded.history) <= 200
    assert bounded.total_born == unbounded.total_born
    assert bounded.total_died == unbounded.total_died
    assert dict(bounded.death_cause_totals()) == dict(unbounded.death_cause_totals())
    # 历史裁剪不消费 rng → 世界演化逐点一致
    assert [s.population for s in bounded.history] == [
        s.population for s in unbounded.history[-200:]
    ]


# ---- ExperimentRunner -------------------------------------------------------


def test_derive_seed_deterministic_and_distinct() -> None:
    a1 = derive_seed(42, 0, 0)
    a2 = derive_seed(42, 0, 0)
    b = derive_seed(42, 1, 0)
    c = derive_seed(43, 0, 0)
    assert a1 == a2
    assert a1 != b
    assert a1 != c


def test_build_plan_matrix_shape() -> None:
    runs = build_plan(base_seed=42, max_generations=10_000, short_generations=250)
    groups = {r.spec.group for r in runs}
    assert groups == {
        "baseline",
        "resource_pressure",
        "resource_distribution",
        "mutation_rate",
        "repeated_seeds",
    }
    by_name = {r.spec.name: r for r in runs}
    assert by_name["baseline"].spec.max_generations == 10_000
    assert by_name["pressure_low"].spec.max_generations == 250
    repeated = [r for r in runs if r.spec.group == "repeated_seeds"]
    assert len(repeated) == 3
    # 同组不同 seed_index → 不同种子
    assert len({r.seed for r in repeated}) == 3


def test_build_plan_baseline_max_ticks_override() -> None:
    runs = build_plan(base_seed=1, baseline_max_ticks=9_000_000)
    baseline = next(r for r in runs if r.spec.name == "baseline")
    assert baseline.spec.max_ticks == 9_000_000
    assert baseline.spec.max_ticks > DEFAULT_MAX_TICKS


def test_build_plan_baseline_max_ticks_auto() -> None:
    """缺省时 baseline tick 上限随世代数自动推导，保证 1,000 代不被截断。"""
    runs = build_plan(base_seed=1, max_generations=1_000)
    baseline = next(r for r in runs if r.spec.name == "baseline")
    assert baseline.spec.max_ticks >= 1_000 * 1_500
    runs_10k = build_plan(base_seed=1, max_generations=10_000)
    baseline_10k = next(r for r in runs_10k if r.spec.name == "baseline")
    assert baseline_10k.spec.max_ticks == 10_000 * 1_800


def test_run_single_deterministic_reproducibility() -> None:
    """同一 spec + 同一 seed → 样本序列逐点相同（deterministic experiments）。"""
    runner = ExperimentRunner(base_seed=11, world_size=(64, 64), tick_interval=500)
    spec = ExperimentSpec("t_det", "baseline", "det test", {}, max_generations=2)
    run = ExperimentRun(spec=spec, seed=derive_seed(11, 0, 0))
    r1 = runner.run_single(run)
    r2 = runner.run_single(run)
    assert r1.samples == r2.samples
    assert r1.summary == r2.summary
    assert r1.config.to_dict() == r2.config.to_dict()
    assert r1.total_ticks == r2.total_ticks


def test_run_single_ends_on_extinction() -> None:
    """资源再生归零 → 种群饿死 → engine_finished + extinct 标记。"""
    runner = ExperimentRunner(base_seed=3, world_size=(64, 64), tick_interval=100)
    spec = ExperimentSpec(
        "t_ext",
        "resource_pressure",
        "no regrowth",
        {"resources": {"regrowth_rate": 0.0}},
        max_generations=100_000,
        max_ticks=400_000,
    )
    run = ExperimentRun(spec=spec, seed=derive_seed(3, 1, 0))
    res = runner.run_single(run)
    assert res.extinct is True
    assert res.ended_reason == "engine_finished"
    assert res.summary["generations_reached"] < 100_000


def test_run_single_reaches_target_generations() -> None:
    runner = ExperimentRunner(base_seed=5, world_size=(64, 64), tick_interval=1_000)
    spec = ExperimentSpec("t_goal", "baseline", "short goal", {}, max_generations=2)
    run = ExperimentRun(spec=spec, seed=derive_seed(5, 0, 0))
    res = runner.run_single(run)
    assert res.finished_normally is True
    assert res.ended_reason == "generations_reached"
    assert res.summary["generations_reached"] >= 2


def test_run_plan_collects_results() -> None:
    runner = ExperimentRunner(base_seed=13, world_size=(64, 64), tick_interval=500)
    runs = [
        ExperimentRun(
            spec=ExperimentSpec(
                "t_a", "baseline", "a", {}, max_generations=1
            ),
            seed=derive_seed(13, 0, 0),
        ),
        ExperimentRun(
            spec=ExperimentSpec(
                "t_b", "baseline", "b", {}, max_generations=1
            ),
            seed=derive_seed(13, 0, 1),
        ),
    ]
    results = runner.run_plan(runs, quiet=True)
    assert set(results) == {"t_a", "t_b"}
    assert all(isinstance(v, ExperimentResult) for v in results.values())


def test_run_plan_immediate_persistence(tmp_path) -> None:
    """out_dir 给定时，每个实验完成即落盘（中途停止不丢已完成结果）。"""
    runner = ExperimentRunner(base_seed=19, world_size=(64, 64), tick_interval=500)
    runs = [
        ExperimentRun(
            spec=ExperimentSpec("t_p1", "baseline", "a", {}, max_generations=1),
            seed=derive_seed(19, 0, 0),
        ),
        ExperimentRun(
            spec=ExperimentSpec("t_p2", "baseline", "b", {}, max_generations=1),
            seed=derive_seed(19, 0, 1),
        ),
    ]
    runner.run_plan(runs, quiet=True, out_dir=tmp_path)
    assert (tmp_path / "t_p1" / "manifest.json").exists()
    assert (tmp_path / "t_p1" / "generations.csv").exists()
    assert (tmp_path / "t_p2" / "manifest.json").exists()


# ---- 持久化 IO --------------------------------------------------------------

_EXPECTED_CSV_KEYS = {
    "tick",
    "generation",
    "span_ticks",
    "born_since_prev",
    "died_since_prev",
    "birth_rate",
    "death_rate",
    *{f"trait_{t}_mean" for t in TRAIT_ORDER},
    *{f"trait_{t}_std" for t in TRAIT_ORDER},
    "population",
    "mean_age",
    "mean_energy",
    "max_generation",
    "median_generation",
    "mean_generation",
    "genome_diversity",
    "unique_genotypes",
    "unique_genotype_ratio",
}


@pytest.fixture(scope="module")
def short_result() -> ExperimentResult:
    runner = ExperimentRunner(base_seed=17, world_size=(64, 64), tick_interval=500)
    spec = ExperimentSpec("t_io", "baseline", "io roundtrip", {}, max_generations=2)
    run = ExperimentRun(spec=spec, seed=derive_seed(17, 0, 0))
    return runner.run_single(run)


def test_save_load_roundtrip(tmp_path, short_result) -> None:
    res = short_result
    assert res.samples, "短实验也应有采样点"
    d = save_experiment(res, tmp_path / "exp")
    assert (d / "manifest.json").exists()
    assert (d / "generations.csv").exists()
    assert (d / "generations.json").exists()

    manifest = load_manifest(d)
    assert manifest["name"] == "t_io"
    assert manifest["n_samples"] == len(res.samples)
    assert manifest["seed"] == res.run.seed
    assert manifest["config"]["seed"] == res.run.seed
    assert "summary" in manifest and "trait_drift" in manifest["summary"]

    rows = load_generations(d)
    assert len(rows) == len(res.samples)
    assert set(rows[0]) == _EXPECTED_CSV_KEYS  # 导出列契约稳定
    # CSV 数值与内存样本一致（genome_diversity 之类按最接近值核对）
    first = json.loads((d / "generations.json").read_text(encoding="utf-8"))[0]
    assert float(first["genome_diversity"]) == pytest.approx(
        res.samples[0].stats.genome_diversity
    )


def test_save_experiment_empty_samples(tmp_path) -> None:
    spec = ExperimentSpec("t_empty", "baseline", "no samples", {}, max_generations=0)
    res = ExperimentResult(
        run=ExperimentRun(spec=spec, seed=1),
        config=SimConfig(seed=1),
        finished_normally=False,
        ended_reason="max_ticks",
        extinct=False,
        total_ticks=0,
        final_population=0,
        duration_s=0.0,
    )
    d = save_experiment(res, tmp_path / "empty")
    assert (d / "generations.csv").read_text(encoding="utf-8").startswith("#")


def test_save_survey(tmp_path, short_result) -> None:
    res = short_result
    root = save_survey({"t_io": res}, tmp_path / "survey")
    assert (root / "t_io" / "manifest.json").exists()
    assert (root / "__survey__.json").exists()


def test_survey_markdown_content(short_result) -> None:
    res = short_result
    from persistence.io import survey_summary_markdown

    out = survey_summary_markdown({"t_io": res})
    assert "t_io" in out
    assert "→" in out  # 性状漂变的 start→end 箭头
    assert "move_prob" in out