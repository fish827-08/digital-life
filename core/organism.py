"""Organism：数字生命个体 —— 位置 + 能量 + 基因组 + 生命周期。

设计原因：
- 行为（本 tick 做什么）由"基因解码出的表现型 + 最小环境视图"共同
  决定（原则 3），规则以协议（EnvironmentView）注入，个体不感知
  具体 World 实现，可替换、可测试（原则 4/6）；
- 死亡判定的"执行者"在引擎/演化层（依据 is_starved/is_expired），
  Organism 只提供状态查询 —— 避免个体自我判死的隐式耦合；
- 所有随机性来自调用方显式传入的 rng（原则 8）。
"""
from __future__ import annotations

from typing import Protocol

import numpy as np

from core import metabolism
from core.genetics import decode
from core.genome import Genome
from core.lifecycle import Lifecycle
from core.metabolism import clamp_energy
from simulation.config import OrganismConfig


class EnvironmentView(Protocol):
    """个体感知环境所需的最小接口（结构契约）。

    由 World 实现；测试可用替身注入，个体与具体世界彻底解耦。
    """

    def resource_at(self, x: int, y: int) -> float: ...

    def consume_resource(self, x: int, y: int, amount: float) -> float: ...

    def random_neighbor(
        self, x: int, y: int, rng: np.random.Generator
    ) -> tuple[int, int]: ...


class Organism:
    """数字生命个体。"""

    __slots__ = (
        "organism_id",
        "x",
        "y",
        "energy",
        "genome",
        "phenotype",
        "lifecycle",
        "config",
    )

    def __init__(
        self,
        *,
        organism_id: int,
        x: int,
        y: int,
        genome: Genome,
        config: OrganismConfig,
        energy: float | None = None,
        phenotype: dict[str, float] | None = None,
        lifecycle: Lifecycle | None = None,
    ) -> None:
        if x < 0 or y < 0:
            raise ValueError(f"位置不能为负：({x}, {y})")
        self.organism_id = organism_id
        self.x = x
        self.y = y
        self.energy = config.initial_energy if energy is None else energy
        self.genome = genome
        self.phenotype = phenotype if phenotype is not None else decode(genome.genes)
        self.lifecycle = lifecycle if lifecycle is not None else Lifecycle()
        self.config = config

    # ---- 状态查询 ------------------------------------------------------

    @property
    def alive(self) -> bool:
        return self.lifecycle.alive

    def is_starved(self) -> bool:
        """能量耗尽的判定（能量 ≤ 0 视为饿死）。"""
        return self.energy <= 0.0

    def is_expired(self) -> bool:
        """寿命到限判定（表现型 life_span 生效）。"""
        return self.lifecycle.expired(self.phenotype["life_span"])

    # ---- 单 tick 行为 ---------------------------------------------------

    def step(self, env: EnvironmentView, rng: np.random.Generator) -> None:
        """执行一个 tick 的个体行为：代谢 → 进食 → 移动 → 年龄推进。

        死亡判定不属于本方法：引擎依据 is_starved()/is_expired()
        决定生死并调用 lifecycle.die() 记录死因（单一职责）。
        """
        cfg = self.config

        # 1) 代谢：基因倍率越高、吃得多 vs 耗得快（选择压的来源之一）
        self.energy -= metabolism.metabolic_consumption(
            cfg.base_metabolism, self.phenotype["metabolism_mult"]
        )
        if self.energy <= 0.0:
            return  # 已无余力进食/移动（死亡判定交给引擎）

        # 2) 进食：在当前格子摄取资源（实际摄入量由环境决定）
        taken = env.consume_resource(self.x, self.y, cfg.eat_amount)
        if taken > 0.0:
            self.energy = clamp_energy(
                self.energy + metabolism.feeding_gain(taken, cfg.eat_efficiency),
                cfg.max_energy,
            )

        # 3) 移动：move_prob 基因决定移动欲望；能量不足以支付移动成本则原地不动
        if rng.random() < self.phenotype["move_prob"] and self.energy >= cfg.move_cost:
            self.x, self.y = env.random_neighbor(self.x, self.y, rng)
            self.energy -= cfg.move_cost

        # 4) 年龄推进
        self.lifecycle.advance()

    def __repr__(self) -> str:
        return (
            f"Organism(id={self.organism_id}, energy={self.energy:.1f}, "
            f"age={self.lifecycle.age}, @({self.x},{self.y}))"
        )