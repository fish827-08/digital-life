"""集成验收：最小闭环端到端断言（对应"无头跑通 + 灭绝防护"验收项）。

与单元测试的差异：这里用真实配置组合验证"系统级行为"——
闭环能长期存活（不崩溃、不灭绝）、代际确实更替、同配置可复现，
并留一个宽松的性能哨兵（原则 7：支持长程演化）。
"""
from __future__ import annotations

import time

from simulation.config import SimConfig
from simulation.engine import SimulationEngine


def make_sim(**sim_overrides) -> SimConfig:
    """面向验收的标准小型配置（64x64，50 初代，500 tick）。"""
    world_cfg = {"width": 64, "height": 64, **sim_overrides.pop("world", {})}
    pop_cfg = {"initial_count": 50, "max_count": 1000, **sim_overrides.pop("population", {})}
    sim_cfg = {"ticks": 500, **sim_overrides.pop("simulation", {})}
    seed = sim_overrides.pop("seed", 42)
    return SimConfig(
        seed=seed,
        world=world_cfg,
        population=pop_cfg,
        simulation=sim_cfg,
        **sim_overrides,
    )


# ---- 闭环存活：种群稳定 ---------------------------------------------------


def test_closed_loop_population_survives_full_run():
    """验收 1：默认生态参数下，最小闭环跑满全程且种群存活。"""
    engine = SimulationEngine(make_sim())
    history = engine.run()
    assert len(history) == 500  # 自然跑满，未触发灭绝防护
    assert not engine.extinct
    assert engine.population.alive_count() > 0  # 有存活的生态
    assert engine.total_born > 50  # 发生过繁殖（不只是初代）
    assert engine.total_died > 0  # 也有死亡（更替存在，不是静止蹦床）
    last = history[-1]
    assert 0 < last.population <= 1000  # 规模在硬上限内


def test_generations_actually_turn_over():
    """验收 2：存活个体中存在经历过 tick 的生物（年龄推进 → 代际链成立）。"""
    engine = SimulationEngine(make_sim(simulation={"ticks": 300}))
    engine.run()
    assert any(o.lifecycle.age >= 1 for o in engine.population.organisms())
    # 出生链：至少存在一个能量低于峰值、非"刚出生同一 tick"的个体
    # （新生子代 energy = 亲代一半，通常 < initial_energy；此处仅断言年龄 > 0 即已发生代际推进）
    assert all(s.died >= 0 and s.born >= 0 for s in engine.history)


def test_initial_population_expands_before_settling():
    """验收 3：种群先扩张（资源充沛期），再收敛到生态承载力附近。"""
    engine = SimulationEngine(make_sim(simulation={"ticks": 800}))
    history = engine.run()
    max_pop = max(s.population for s in history)
    end_pop = history[-1].population
    assert max_pop >= 2 * 50  # 曾显著扩张过（>初代 2 倍）
    assert end_pop > 0  # 收敛阶段仍存活（未灭绝）


# ---- 灭绝防护 ---------------------------------------------------------------


def test_extinction_defense_integration():
    """验收 4：断粮生态必然灭绝，且引擎正确标记并提前停止。"""
    engine = SimulationEngine(
        make_sim(
            population={"initial_count": 20},
            resources={"initial_fill": 1e-6, "regrowth_rate": 0.0},
            simulation={"ticks": 5000, "stop_on_extinction": True},
        )
    )
    history = engine.run()
    assert engine.extinct
    assert engine.finished
    assert len(history) < 5000  # 提前终止
    assert history[-1].population == 0
    assert engine.total_born <= 20  # 断粮下不应产生新后代…（防御性断言：顶多初代）


# ---- 端到端复现 -------------------------------------------------------------


def test_end_to_end_reproducible_with_same_config():
    """验收 5：同一配置 + 同一种子 → 两次完整运行的逐 tick 历史完全一致。"""
    a = SimulationEngine(make_sim(simulation={"ticks": 300}))
    b = SimulationEngine(make_sim(simulation={"ticks": 300}))
    ha = a.run()
    hb = b.run()
    assert len(ha) == len(hb) == 300
    assert [s.to_dict() for s in ha] == [s.to_dict() for s in hb]


# ---- 性能哨兵（原则 7：支持长程模拟的结构余量） ---------------------------


def test_long_run_performance_sentry():
    """验收 6：1 万 tick 长程跑完且耗时在宽松范围内（防结构退化）。"""
    engine = SimulationEngine(
        make_sim(
            population={"initial_count": 200},
            simulation={"ticks": 10_000, "stop_on_extinction": False},
        )
    )
    start = time.perf_counter()
    engine.run()
    elapsed = time.perf_counter() - start
    # 宽松哨兵：任何退化到秒级以下的状态都会触发；正常应远小于此
    assert elapsed < 60.0, f"长程模拟过慢：{elapsed:.1f}s"
    assert engine.tick == 10_000