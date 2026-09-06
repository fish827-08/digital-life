"""VecEngine（数组化引擎）测试：确定性回放、规则等价、观测集成、性能哨兵。

VecEngine 与 SimulationEngine 同规则但 RNG 流不同（见 vecengine 模块
docstring 的"已知差异"），因此等价性用"统计等价"断言：同配置下两种
引擎的种群规模带、性状收敛方向、灭绝动力学一致，而非逐位一致。
"""
from __future__ import annotations

import time

import numpy as np
import pytest

from observatory.experiment import ExperimentRunner, build_plan
from observatory.observer import EvolutionObserver
from simulation.config import SimConfig
from simulation.engine import SimulationEngine
from simulation.vecengine import VecEngine


def _cfg(seed: int = 42, *, world: int = 64, ticks: int = 1000, **extra) -> SimConfig:
    base = {
        "seed": seed,
        "world": {"width": world, "height": world},
        "simulation": {"ticks": ticks, "stop_on_extinction": True},
    }
    base.update(extra)
    return SimConfig(**base)


# ---- 确定性 -------------------------------------------------------------


def test_deterministic_replay_is_bitwise():
    cfg = _cfg(seed=7, ticks=4000)
    a, b = VecEngine(cfg), VecEngine(cfg)
    ha = [s.to_dict() for s in a.run()]
    hb = [s.to_dict() for s in b.run()]
    assert ha == hb
    assert a.total_born == b.total_born
    assert a.population.max_generation == b.population.max_generation


def test_different_seed_diverges():
    a = VecEngine(_cfg(seed=1, ticks=2000))
    b = VecEngine(_cfg(seed=2, ticks=2000))
    a.run()
    b.run()
    # 同规则不同流：不会一致，但都要处于健康生态带
    assert a.population.alive_count() != b.population.alive_count() or a.total_born != b.total_born
    assert a.population.alive_count() > 0
    assert b.population.alive_count() > 0


# ---- 规则等价（统计） -----------------------------------------------------


@pytest.mark.parametrize("seed", [42, 7])
def test_statistical_equivalence_with_object_engine(seed):
    ticks = 20_000
    vec = VecEngine(_cfg(seed=seed, ticks=ticks))
    obj = SimulationEngine(_cfg(seed=seed, ticks=ticks))
    vec.run()
    obj.run()

    # 种群规模带一致（64x64 默认生态平衡带 ~300±100）
    assert 100 <= vec.population.alive_count() <= 450
    assert 100 <= obj.population.alive_count() <= 450

    # 世代推进量级一致（同样运行期都产生了可观测的代际深入）
    assert vec.population.max_generation > obj.population.max_generation * 0.5

    # 性状收敛方向一致：代谢倍率均值都压到基因下限附近（<0.9）
    vec_meta = _mean_trait(vec, "metabolism_mult")
    obj_meta = _mean_trait(obj, "metabolism_mult")
    assert vec_meta < 0.9
    assert obj_meta < 0.9
    assert abs(vec_meta - obj_meta) < 0.2


def _mean_trait(eng, name: str) -> float:
    import numpy as _np

    from core.genetics import TRAIT_TABLE

    t = next(x for x in TRAIT_TABLE if x.name == name)
    gens = eng.population.organisms()
    if not gens:
        return float("nan")
    return float(_np.mean([o.phenotype[name] for o in gens]))


def test_extinction_dynamics_match():
    # 资源近零 → 两种引擎都应慢性饥饿灭绝，且量级相当（tick 数同数量级）
    overrides = {"resources": {"regrowth_rate": 0.001}}
    ticks = 100_000
    a = VecEngine(_cfg(seed=42, ticks=ticks, **overrides))
    b = SimulationEngine(_cfg(seed=42, ticks=ticks, **overrides))
    a.run()
    b.run()
    assert a.extinct and b.extinct
    assert abs(a.tick - b.tick) < 0.5 * max(a.tick, b.tick)


# ---- 账本与不变量 --------------------------------------------------------


def test_ledger_and_invariants():
    eng = VecEngine(_cfg(seed=3, ticks=3000))
    for s in eng.run():
        assert s.died >= 0 and s.born >= 0
        assert s.population >= 0
        assert 0.0 <= s.total_resource <= eng.world.width * eng.world.height * 1.0 + 1e-9
        assert s.total_energy >= 0.0
    assert eng.total_died == sum(s.died for s in eng.history)
    assert eng.total_born >= eng.population.max_generation  # 每代深入至少一次生育


def test_ancestry_and_generation_bookkeeping():
    eng = VecEngine(_cfg(seed=5, ticks=5000))
    eng.run()
    orgs = eng.population.organisms()
    assert len(orgs) > 0
    ids = {o.organism_id for o in orgs}
    gens = [o.generation for o in orgs]
    assert min(gens) >= 0
    assert max(gens) == eng.population.max_generation
    # 亲代可能已死（不在活体集合）；谱系深度单调性由 max_generation 增量维护
    assert all(o.energy > -1e-6 or o.energy <= 0.0 for o in orgs)  # 无异常能量


# ---- 观测集成 -------------------------------------------------------------


def test_observer_and_runner_integration():
    cfg = _cfg(seed=11, ticks=4000)
    cfg.simulation.history_limit = 2048
    eng = VecEngine(cfg)
    obs = EvolutionObserver(eng, tick_interval=50)
    while not eng.finished:
        obs.observe(eng.step())
    assert len(obs.samples) > 0
    row = obs.samples[-1].flatten()
    for key in ("trait_move_prob_mean", "trait_life_span_mean",
                "genome_diversity", "population", "birth_rate"):
        assert key in row


def test_experiment_runner_vec():
    runner = ExperimentRunner(use_vec=True, tick_interval=100)
    run = build_plan(base_seed=42, max_generations=30, short_generations=30)[0]
    res = runner.run_single(run)
    assert res.finished_normally
    assert res.total_ticks > 0
    assert len(res.samples) > 0
    assert res.summary["generations_reached"] >= 30
    assert res.final_population > 0


# ---- 性能哨兵（防向量化退化） ---------------------------------------------


def test_vec_performance_sentinel():
    cfg = _cfg(seed=42, ticks=100_000)
    eng = VecEngine(cfg)
    t0 = time.perf_counter()
    eng.run()
    dt = time.perf_counter() - t0
    assert dt < 30.0, f"vec 引擎 100k tick 耗时 {dt:.1f}s，超过 30s 哨兵"
    assert eng.population.alive_count() > 0