"""Environment：core.EnvironmentView 协议的具体环境实现。

设计原因：
- core 层只声明个体"需要的能力"（协议），这里给出落实：
  坐标包装（torus / 边界）、资源查询与消费、邻格选择（尊重地形）；
- 不持有个体引用，纯环境原语：Organism.step() 每次调用都通过本对象；
- 边界处理策略：热路径（邻格选择）用显式分支避免异常开销；
  逻辑错误（wrap 关闭时查询越界坐标）抛 IndexError 快速暴露 bug。
"""
from __future__ import annotations

import numpy as np

from world.resource import ResourceField
from world.terrain import TerrainField

NEIGHBOR_RETRY = 8  # 找可通行邻格的尝试次数上限


class Environment:
    """EnvironmentView 协议实现（世界对个体的最小环境视图）。"""

    __slots__ = ("width", "height", "wrap", "resources", "terrain")

    def __init__(
        self,
        width: int,
        height: int,
        wrap: bool,
        resources: ResourceField,
        terrain: TerrainField,
    ) -> None:
        self.width = width
        self.height = height
        self.wrap = wrap
        self.resources = resources
        self.terrain = terrain

    # ---- EnvironmentView 协议方法 ----------------------------------------

    def resource_at(self, x: int, y: int) -> float:
        """查询逻辑坐标 (x, y) 处的资源存量（自动包装坐标）。"""
        nx, ny = self._norm(x, y)
        return self.resources.amount_at(nx, ny)

    def consume_resource(self, x: int, y: int, amount: float) -> float:
        """消费逻辑坐标 (x, y) 处的资源，返回实际消费量。"""
        nx, ny = self._norm(x, y)
        return self.resources.consume(nx, ny, amount)

    def random_neighbor(
        self, x: int, y: int, rng: np.random.Generator
    ) -> tuple[int, int]:
        """随机找一个可通行的 8 邻格；找不到则原地不动（返回 (x, y)）。"""
        for _ in range(NEIGHBOR_RETRY):
            dx = int(rng.integers(-1, 2))
            dy = int(rng.integers(-1, 2))
            if dx == 0 and dy == 0:
                continue
            nx, ny = x + dx, y + dy
            if self.wrap:
                nx %= self.width
                ny %= self.height
            elif not (0 <= nx < self.width and 0 <= ny < self.height):
                continue  # 非 wrap 边界：跳过越界候选
            if self.terrain.is_passable(nx, ny):
                return nx, ny
        return x, y

    # ---- 内部 -------------------------------------------------------------

    def _norm(self, x: int, y: int) -> tuple[int, int]:
        """逻辑坐标 → 原始网格坐标（torus 包装 / 越界报错）。"""
        if self.wrap:
            return int(x % self.width), int(y % self.height)
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise IndexError(
                f"坐标越界: ({x}, {y})，世界 {self.width}x{self.height}（wrap 关闭）"
            )
        return int(x), int(y)