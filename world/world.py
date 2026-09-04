"""World：世界装配与总控 —— 资源场 × 地形场 × 环境接口。

设计原因：
- 组合优于继承：World 拥有 ResourceField / TerrainField / Environment
  三个子对象，对外只露"整体"语义（环境访问、随机可通行格、每 tick
  再生推进、资源总量、快照）；
- 从 SimConfig 确定性构造：同配置 + 同种子 → 完全相同的世界
  （可复现，原则 8）；
- World 不直接理解 Organism/Population：个体如何用世界由
  EnvironmentView 协议约束（core 层），种群如何摆进去由演化层负责。
"""
from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from simulation.config import SimConfig
from world.environment import Environment
from world.resource import ResourceField
from world.terrain import TerrainField


class World:
    """由配置确定性构造的世界。"""

    __slots__ = ("config", "width", "height", "wrap", "resources", "terrain", "environment")

    def __init__(self, config: SimConfig, rng: np.random.Generator) -> None:
        self.config = config
        self.width = config.world.width
        self.height = config.world.height
        self.wrap = config.world.wrap
        self.resources = ResourceField(self.width, self.height, config.resources, rng)
        self.terrain = TerrainField(self.width, self.height)
        self.environment = Environment(
            self.width, self.height, self.wrap, self.resources, self.terrain
        )

    # ---- 每 tick 推进 ------------------------------------------------------

    def tick_regrowth(self) -> None:
        """资源再生（由引擎在个体行动结束后调用）。"""
        self.resources.regrow()

    # ---- 查询与统计 ---------------------------------------------------------

    def random_passable_cell(self, rng: np.random.Generator) -> tuple[int, int]:
        """随机返回一个可通行格（种群出生点选址用）。"""
        while True:
            x = int(rng.integers(0, self.width))
            y = int(rng.integers(0, self.height))
            if self.terrain.is_passable(x, y):
                return x, y

    def total_resource(self) -> float:
        return self.resources.total()

    def resource_snapshot(self) -> NDArray[np.float64]:
        return self.resources.snapshot()

    def __repr__(self) -> str:
        return (
            f"World({self.width}x{self.height}, wrap={self.wrap}, "
            f"total={self.total_resource():.1f})"
        )