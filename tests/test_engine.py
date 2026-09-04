"""SimulationEngine 测试：确定性、闭环推进、灭绝防护。"""
from __future__ import annotations

import pytest

from simulation.config import SimConfig
from simulation.engine import SimulationEngine


def make_engine(**sim_overrides) -> SimulationEngine:
    """构造一个 32x32、50 初代的小型引擎，支持按组合并覆盖。"""
    world_cfg = {"width": 32, "height": 32, **sim_overrides.pop("world", {})}
    pop_cfg = {"initial_count": 50, "max_count": 500, **sim_overrides.pop("population", {})}
    sim_cfg = {"ticks": 200, **sim_overrides.pop("simulation", {})}
    seed = sim_overrides.pop("seed", 1)
    cfg = SimConfig(
        seed=seed,
        world=world_cfg,
        population=pop_cfg,
        simulation=sim_cfg,
        **sim_overrides,
    )
    return SimulationEngine(cfg)


# ---- 构造 ------------------------------------------------------------


def test_constructor_assembles_and_spawns():
    engine = make_engine()
    assert len(engine.population) == 50  # 初代全部出生
    assert engine.spawn_report.born == 50
    assert engine.tick == 0
    assert not engine.extinct and not engine.finished
    assert len(engine.history) == 0
    assert engine.world.width == 32 and engine.world.height == 32


def test_same_seed_same_world_layout():
    a = make_engine(seed=5, population={"initial_count": 20})
    b = make_engine(seed=5, population={"initial_count": 20})
    assert (a.world.resource_snapshot() == b.world.resource_snapshot()).all()


# ---- step 推进 -----------------------------------------------------------


def test_step_advances_and_records_stats():
    engine = make_engine()
    for i in range(5):
        s = engine.step()
        assert s.tick == i
        assert engine.tick == i + 1
        assert len(engine.history) == i + 1
        assert s.population == engine.population.alive_count()
        assert s.total_energy >= 0.0
        assert s.total_resource >= 0.0
        assert s.born >= 0 and s.died >= 0
        assert sum(v for v in s.deaths_by_cause.values()) == s.died


def test_step_after_finished_raises():
    engine = make_engine(simulation={"ticks": 3})
    engine.run()
    with pytest.raises(RuntimeError):
        engine.step()


# ---- run：确定性 -----------------------------------------------------


def test_run_is_deterministic_tick_by_tick():
    a = make_engine(seed=9, simulation={"ticks": 100})
    b = make_engine(seed=9, simulation={"ticks": 100})
    ha = a.run()
    hb = b.run()
    assert len(ha) == len(hb) == 100
    assert [s.to_dict() for s in ha] == [s.to_dict() for s in hb]


def test_run_stops_at_tick_limit():
    engine = make_engine(simulation={"ticks": 37})
    history = engine.run()
    assert len(history) == 37
    assert engine.tick == 37
    assert engine.finished
    assert engine.history[-1].tick == 36  # tick 从 0 编号


def test_run_with_smaller_override_truncates():
    engine = make_engine(simulation={"ticks": 200})
    history = engine.run(ticks=10)
    assert len(history) == 10
    assert engine.tick == 10
    assert not engine.extinct
    assert not engine.finished  # 按配置 200 tick 判定，仍未结束 → 可继续推进
    engine.step()  # 截断后引擎仍可调用


# ---- 灭绝防护 -----------------------------------------------------------


def test_extinction_stops_early_and_flags():
    # 无食物 + 无再生 → 必然饿死；世代 < 200 tick，验证提前终止
    engine = make_engine(
        population={"initial_count": 20},
        resources={"initial_fill": 1e-6, "regrowth_rate": 0.0},
        simulation={"ticks": 500, "stop_on_extinction": True},
    )
    history = engine.run()
    assert engine.extinct
    assert engine.finished
    assert len(history) < 500  # 提前停
    assert history[-1].population == 0


def test_stop_on_extinction_false_runs_to_limit():
    engine = make_engine(
        population={"initial_count": 20},
        resources={"initial_fill": 1e-6, "regrowth_rate": 0.0},
        simulation={"ticks": 500, "stop_on_extinction": False},
    )
    history = engine.run()
    assert engine.extinct  # 灭绝事实仍然标记
    assert len(history) == 500  # 但不提前停，空转跑满
    assert all(s.population == 0 for s in history[-10:])


def test_no_food_energy_strictly_decreases():
    """无食物时能量只减不增（代谢恒正）——能量守恒的方向性检验。"""
    engine = make_engine(
        population={"initial_count": 20},
        resources={"initial_fill": 1e-6, "regrowth_rate": 0.0},
        simulation={"ticks": 80, "stop_on_extinction": False},
    )
    history = engine.run()
    for prev, cur in zip(history, history[1:]):
        if prev.population > 0:
            assert cur.total_energy <= prev.total_energy


# ---- 汇总统计 ---------------------------------------------------------


def test_totals_aggregate_over_history():
    engine = make_engine()
    engine.run()
    assert engine.total_born == 50 + sum(s.born for s in engine.history)
    assert engine.total_died == sum(s.died for s in engine.history)
    deaths = engine.death_cause_totals()
    assert sum(deaths.values()) == engine.total_died


def test_history_dict_snapshot_is_json_safe():
    engine = make_engine()
    engine.run(ticks=20)
    for s in engine.history:
        d = s.to_dict()
        assert set(d) == {
            "tick", "population", "born", "died", "deaths",
            "total_energy", "total_resource",
        }
        assert all(isinstance(k, str) for k in d["deaths"])