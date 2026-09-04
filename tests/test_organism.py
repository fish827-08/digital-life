"""Organism 个体测试：构造、单 tick 行为序列、死亡判定接口。"""
from __future__ import annotations

import numpy as np
import pytest

from core.genome import Genome
from core.lifecycle import Lifecycle
from core.organism import Organism
from simulation.config import OrganismConfig

CFG = OrganismConfig()


def make_genome(gene0: float, gene1: float = 1 / 3) -> Genome:
    """构造测试基因链（move_prob, metabolism_mult）。

    gene1=1/3 时解码出的 metabolism_mult 恰好为 1.0（线性映射中点），
    便于按"基础代谢 1.0"直接心算期望能量。
    """
    genes = np.zeros(16)
    genes[0] = gene0
    genes[1] = gene1
    return Genome(genes)


class FakeEnv:
    """EnvironmentView 的测试替身（协议注入）。"""

    def __init__(self, resource: float = 0.0):
        self.resource = resource
        self.consume_calls: list[tuple[int, int, float]] = []
        self.neighbor_calls: list[tuple[int, int]] = []

    def resource_at(self, x: int, y: int) -> float:
        return self.resource

    def consume_resource(self, x: int, y: int, amount: float) -> float:
        self.consume_calls.append((x, y, amount))
        taken = min(amount, self.resource)
        self.resource -= taken
        return taken

    def random_neighbor(self, x: int, y: int, rng: np.random.Generator) -> tuple[int, int]:
        self.neighbor_calls.append((x, y))
        return (x + 1, y)


def make_organism(
    rng: np.random.Generator,
    gene0: float = 0.0,
    *,
    x: int = 5,
    y: int = 5,
    energy: float | None = None,
    genome: Genome | None = None,
    lifecycle: Lifecycle | None = None,
) -> Organism:
    return Organism(
        organism_id=1,
        x=x,
        y=y,
        genome=genome if genome is not None else make_genome(gene0),
        config=CFG,
        energy=energy,
        lifecycle=lifecycle,
    )


# ---- 构造 -------------------------------------------------------------


def test_construction_defaults():
    o = make_organism(np.random.default_rng(0))
    assert o.organism_id == 1
    assert (o.x, o.y) == (5, 5)
    assert o.energy == CFG.initial_energy
    assert o.alive
    assert o.lifecycle.age == 0
    assert o.phenotype["move_prob"] == 0.0  # 表现型已按基因解码缓存


def test_negative_position_rejected():
    with pytest.raises(ValueError):
        make_organism(np.random.default_rng(0), x=-1, y=0)


# ---- 死亡判定接口 -----------------------------------------------------


def test_starvation_flag():
    o = make_organism(np.random.default_rng(0), energy=0.0)
    assert o.is_starved()
    o_alive = make_organism(np.random.default_rng(0), energy=10.0)
    assert not o_alive.is_starved()


def test_expired_flag_uses_phenotype_lifespan():
    # life_span 基因位=1 → 解码为 4000；构造 4000 岁个体验证到限判定
    o = make_organism(
        np.random.default_rng(0), genome=Genome(np.ones(16)),
        lifecycle=Lifecycle(initial_age=4000),
    )
    assert o.is_expired()
    o2 = make_organism(
        np.random.default_rng(0), genome=Genome(np.ones(16)),
        lifecycle=Lifecycle(initial_age=3999),
    )
    assert not o2.is_expired()


# ---- 单 tick 行为 -----------------------------------------------------


def test_step_pays_metabolism():
    env = FakeEnv(resource=0.0)  # 无食物
    o = make_organism(np.random.default_rng(0), gene0=0.0)  # 不移动
    o.step(env, np.random.default_rng(0))
    assert o.energy == pytest.approx(CFG.initial_energy - CFG.base_metabolism)
    # "尝试进食"是本该发生的动作，只是环境没给到食物 → 获得 0 能量
    assert env.consume_calls == [(5, 5, CFG.eat_amount)]


def test_step_eats_and_gains_energy():
    env = FakeEnv(resource=1.0)
    o = make_organism(np.random.default_rng(0), gene0=0.0)
    o.step(env, np.random.default_rng(0))
    # 60 - 0.6(代谢) + 0.5*3(进食) = 60.9
    assert o.energy == pytest.approx(
        CFG.initial_energy - CFG.base_metabolism + CFG.eat_amount * CFG.eat_efficiency
    )
    assert env.consume_calls == [(5, 5, CFG.eat_amount)]
    assert env.resource == pytest.approx(1.0 - CFG.eat_amount)  # 环境资源被实际扣除


def test_step_moves_when_move_prob_one():
    env = FakeEnv(resource=0.0)
    o = make_organism(np.random.default_rng(0), gene0=1.0)
    o.step(env, np.random.default_rng(0))
    assert (o.x, o.y) == (6, 5)  # FakeEnv 总是返回 (x+1, y)
    assert env.neighbor_calls == [(5, 5)]
    # 60 - 0.6(代谢) - 0.4(移动) = 59.0
    assert o.energy == pytest.approx(
        CFG.initial_energy - CFG.base_metabolism - CFG.move_cost
    )


def test_step_not_move_when_move_prob_zero():
    env = FakeEnv(resource=0.0)
    o = make_organism(np.random.default_rng(0), gene0=0.0)
    o.step(env, np.random.default_rng(0))
    assert (o.x, o.y) == (5, 5)
    assert not env.neighbor_calls


def test_step_skips_move_when_unaffordable():
    env = FakeEnv(resource=0.0)
    o = make_organism(np.random.default_rng(0), gene0=1.0, energy=0.6)
    o.step(env, np.random.default_rng(0))
    assert (o.x, o.y) == (5, 5)  # 代谢后 0.6-1.0 < 0，无力移动
    assert not env.neighbor_calls


def test_step_advances_age():
    env = FakeEnv(resource=0.0)
    o = make_organism(np.random.default_rng(0), gene0=0.0)
    o.step(env, np.random.default_rng(0))
    assert o.lifecycle.age == 1


def test_step_is_deterministic_with_seed():
    env_a, env_b = FakeEnv(resource=1.0), FakeEnv(resource=1.0)
    oa = make_organism(np.random.default_rng(0), gene0=0.5, energy=50.0)
    ob = make_organism(np.random.default_rng(0), gene0=0.5, energy=50.0)
    oa.step(env_a, np.random.default_rng(9))
    ob.step(env_b, np.random.default_rng(9))
    assert oa.energy == ob.energy
    assert (oa.x, oa.y) == (ob.x, ob.y)