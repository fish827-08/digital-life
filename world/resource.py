"""ResourceField：资源场 —— 网格上的可再生资源存量。

设计原因：
- 用 NumPy 二维 float64 数组承载整场资源，一次 regrow 全场向量化，
  为"百万级模拟"的量级性能打底（原则 7）；
- 本类不知道坐标包装（torus / 边界）：那是 Environment 的职责。
  传入本类的坐标永远是"原始网格坐标"，越界会让 NumPy 自然抛
  IndexError —— 保证调用方（Environment）内部逻辑正确性可被发现。
"""
from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from simulation.config import ResourceConfig


class ResourceField:
    """资源场。网格布局：grid[y][x]。"""

    __slots__ = ("width", "height", "capacity", "regrowth_rate", "_grid")

    def __init__(
        self, width: int, height: int, config: ResourceConfig, rng: np.random.Generator
    ) -> None:
        self.width = width
        self.height = height
        self.capacity = config.capacity
        self.regrowth_rate = config.regrowth_rate
        # 每个格子的初始资源在 [0, capacity×initial_fill) 内随机（可复现）
        self._grid = rng.uniform(
            0.0, config.capacity * config.initial_fill, size=(height, width)
        )

    # ---- 查询与消费 ------------------------------------------------------

    def amount_at(self, x: int, y: int) -> float:
        """查询 (x, y) 资源存量（原始坐标，不做包装）。"""
        return float(self._grid[y, x])

    def consume(self, x: int, y: int, amount: float) -> float:
        """尝试消耗：最多消费可用量，返回实际消耗量。"""
        available = self._grid[y, x]
        taken = min(amount, available)
        if taken > 0:
            self._grid[y, x] = available - taken
        return float(taken)

    # ---- 环境推进与统计 --------------------------------------------------

    def regrow(self) -> None:
        """全场再生（向量化）：每格 += regrowth_rate，上限 capacity。"""
        np.minimum(self.capacity, self._grid + self.regrowth_rate, out=self._grid)

    def total(self) -> float:
        """全场资源总量（统计/可视化用）。"""
        return float(self._grid.sum())

    def snapshot(self) -> NDArray[np.float64]:
        """返回当前资源场的拷贝（快照，供统计/可视化，不改内部状态）。"""
        return self._grid.copy()

    def __repr__(self) -> str:
        return (
            f"ResourceField({self.width}x{self.height}, "
            f"total={self.total():.1f}/{self.width * self.height * self.capacity:.1f})"
        )