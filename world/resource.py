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
        fill_cap = config.capacity * config.initial_fill
        if config.patchiness <= 0.0:
            # 均匀：每个格子在 [0, capacity×initial_fill) 内随机（可复现）
            # 注意保持这一支的 RNG 调用序列与历史版本完全一致（确定性兼容）。
            self._grid = rng.uniform(0.0, fill_cap, size=(height, width))
        else:
            # 块状异质：先把网格分成 patch_count×patch_count 块，每块一个
            # 独立的初始填充率（在 initial_fill±patchiness 内随机），格内再
            # 均匀采样 —— 制造"富饶斑块 / 贫瘠斑块"的空间结构。
            blocks = max(1, config.patch_count)
            bh = (height + blocks - 1) // blocks  # 每块至少 1 行
            bw = (width + blocks - 1) // blocks
            nh, nw = (height + bh - 1) // bh, (width + bw - 1) // bw
            low = max(0.0, config.initial_fill * (1.0 - config.patchiness))
            high = min(1.0, config.initial_fill * (1.0 + config.patchiness))
            block_fill = rng.uniform(low, high, size=(nh, nw))
            grid = np.zeros((height, width), dtype=np.float64)
            for by in range(nh):
                y0, y1 = by * bh, min(height, (by + 1) * bh)
                for bx in range(nw):
                    x0, x1 = bx * bw, min(width, (bx + 1) * bw)
                    grid[y0:y1, x0:x1] = rng.uniform(
                        0.0,
                        fill_cap * block_fill[by, bx],
                        size=(y1 - y0, x1 - x0),
                    )
            self._grid = grid

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

    def consume_at_flat(
        self,
        flat: NDArray[np.int64],
        amount: float,
    ) -> NDArray[np.float64]:
        """批量消费（数组化引擎用）：同一格多点取食按"均分封顶"分配。

        每格总消耗 = min(存量, amount × 使用格数)，资源不会变负，
        结果与调用顺序无关（确定性更强）。flat = y×width+x 平铺索引，
        返回与入参一一对应的实际消费量数组（每格均分份额）。
        """
        flat = np.asarray(flat, dtype=np.int64)
        grid_flat = self._grid.reshape(-1)
        avail = grid_flat[flat]
        cnt = np.zeros(grid_flat.size, dtype=np.int64)
        np.add.at(cnt, flat, 1)
        taken = np.minimum(amount, avail / np.maximum(1, cnt[flat]))
        np.add.at(grid_flat, flat, -taken)
        return taken

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