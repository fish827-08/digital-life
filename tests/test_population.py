"""Population 种群容器测试：出生、逐 tick 推进、繁殖、死亡、上限。"""
from __future__ import annotations

import numpy as np
import pytest

from core.genome import Genome
from core.lifecycle import DeathCause
from core.organism import Organism
from evolution.population import Population
from simulation.config import SimConfig
from world.world import World

# 测试代：全中立（gene0=0 不移动、gene1=0 代谢 0.5、gene2=0 阈值 0.25、gene3=0 寿命 200）
TEST_GENOME = Genome(np.zeros(16))
HIGH_ENERGY = 300.0


def make_pop(**sim_overrides) -> tuple[Population, World, SimConfig]:
    default_pop = {"initial_count": 5, "max_count": 500}
    pop_cfg = {**default_pop, **sim_overrides.pop("population", {})}
    cfg = SimConfig(
        seed=1,
        world={"width": 16, "height": 16},
        population=pop_cfg,
        **sim_overrides,
    )
    world = World(cfg, np.random.default_rng(cfg.seed))
    pop = Population(cfg, world)
    return pop, world, cfg


def rig_for_reproduction(pop: Population) -> None:
    """把所有个体改装成"必然能繁殖"的测试对象。"""
    for o in pop.organisms():
        o.genome = TEST_GENOME
        o.phenotype = {  # 与 TEST_GENOME 的解码结果一致
            "move_prob": 0.0,
            "metabolism_mult": 0.5,
            "repro_fraction": 0.25,
            "life_span": 200.0,
        }
        o.energy = HIGH_ENERGY


# ---- 出生 -----------------------------------------------------------------


def test_spawn_initial_count_and_ids():
    pop, world, cfg = make_pop()
    report = pop.spawn_initial(np.random.default_rng(cfg.seed))
    assert report.born == cfg.population.initial_count
    assert len(pop) == cfg.population.initial_count
    ids = [o.organism_id for o in pop.organisms()]
    assert ids == list(range(cfg.population.initial_count))  # ID 连续
    for o in pop.organisms():
        assert 0 <= o.x < world.width and 0 <= o.y < world.height
        assert world.terrain.is_passable(o.x, o.y)


def test_spawn_is_deterministic_with_seed():
    pop_a, _, cfg_a = make_pop()
    pop_b, _, cfg_b = make_pop()
    ra = pop_a.spawn_initial(np.random.default_rng(9))
    rb = pop_b.spawn_initial(np.random.default_rng(9))
    assert ra.born == rb.born == cfg_a.population.initial_count
    a = [(o.x, o.y) for o in pop_a.organisms()]
    b = [(o.x, o.y) for o in pop_b.organisms()]
    assert a == b
    assert cfg_a.population == cfg_b.population


# ---- 每 tick 推进 ------------------------------------------------------------


def test_update_reproduces_and_children_on_parent_cell():
    pop, _, cfg = make_pop()
    pop.spawn_initial(np.random.default_rng(cfg.seed))
    rig_for_reproduction(pop)
    parents = {o.organism_id: o for o in pop.organisms()}
    # 清空亲代格子的食物，让能量心算完全确定：300 - 0.3(代谢=0.6×0.5) = 299.7 → 对半各 149.85
    for o in pop.organisms():
        pop.world.environment.consume_resource(o.x, o.y, 1e9)

    report = pop.update(np.random.default_rng(7))

    assert report.born == len(parents)  # 个个繁殖一次
    assert len(pop) == len(parents) * 2
    for pid in parents:
        assert pop.get(pid).energy == pytest.approx(149.85)  # 亲代能量对半支付
    # 子代 ID 从 initial_count 起连续、与亲代同格、能量守恒
    for cid in range(len(parents), len(parents) * 2):
        child = pop.get(cid)
        parent = pop.get(cid - len(parents))
        assert (child.x, child.y) == (parent.x, parent.y)
        assert child.energy == pytest.approx(149.85)


def test_update_respects_population_cap():
    pop, _, _ = make_pop(population={"initial_count": 5, "max_count": 6})
    pop.spawn_initial(np.random.default_rng(3))
    rig_for_reproduction(pop)
    report = pop.update(np.random.default_rng(3))
    assert len(pop) == 6  # 硬上限
    assert report.born == 1  # 只允许再出生 1 个


def test_update_removes_dead():
    pop, _, cfg = make_pop()
    pop.spawn_initial(np.random.default_rng(cfg.seed))
    for o in pop.organisms():
        o.energy = 0.0  # 全部饿死
    report = pop.update(np.random.default_rng(0))
    assert report.died == 5
    assert len(pop) == 0
    assert report.deaths_by_cause[DeathCause.STARVATION] == 5


def test_update_report_is_consistent():
    pop, _, cfg = make_pop()
    pop.spawn_initial(np.random.default_rng(cfg.seed))
    report = pop.update(np.random.default_rng(1))
    assert report.population == len(pop)
    assert report.population == 5 + report.born - report.died
    assert pop.total_energy() >= 0.0
    for o in pop.organisms():
        assert o.alive  # 库里不应残留尸体