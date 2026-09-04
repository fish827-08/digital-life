"""TerrainField：地形场 —— 每个格子是否可通行。

设计原因：
- v1 暂无障碍：所有格子默认可通行。但"可否通行"的判定结构已就位，
  后续加水域 / 岩壁 / 毒区时只改这里，行为层（Environment 的邻格
  选择）不需要动（原则 4/6）；
- 布局与 ResourceField 一致：grid[y][x]，便于将来叠加。
"""
from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


class TerrainField:
    """地形场。v1 = 全通行的布尔网格。"""

    __slots__ = ("width", "height", "_passable")

    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self._passable: NDArray[np.bool_] = np.ones((height, width), dtype=bool)

    # ---- 查询与修改 ------------------------------------------------------

    def is_passable(self, x: int, y: int) -> bool:
        """查询 (x, y) 是否可通行（原始坐标，越界抛 IndexError）。"""
        return bool(self._passable[y, x])

    def set_passable(self, x: int, y: int, value: bool) -> None:
        """显式设置通行性（测试 / 未来环境编辑用）。"""
        self._passable[y, x] = bool(value)

    def blocked_count(self) -> int:
        """不可通行格数量（统计用）。"""
        return int((~self._passable).sum())

    def snapshot(self) -> NDArray[np.bool_]:
        return self._passable.copy()

    def __repr__(self) -> str:
        blocked = int((~self._passable).sum())
        return f"TerrainField({self.width}x{self.height}, blocked={blocked})"