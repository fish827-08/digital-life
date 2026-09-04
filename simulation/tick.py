"""TickStats：单 tick 结束后的种群/世界快照（统计账本）。

设计原因：
- 引擎按节拍产生不可变的统计快照，历史即"全程录像"：复现验证、
  事后分析与存档恢复共用同一份数据（原则 8）；
- to_dict() 输出 JSON 安全结构（枚举 → 字符串），便于落盘与
  逐 tick 等价比较（确定性断言）。
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from core.lifecycle import DeathCause


@dataclass(frozen=True)
class TickStats:
    """一个 tick 结束时的可观测状态。"""

    tick: int
    population: int
    born: int
    died: int
    deaths_by_cause: Counter
    total_energy: float
    total_resource: float

    def to_dict(self) -> dict:
        deaths = {
            (
                cause.value
                if isinstance(cause, DeathCause)
                else str(cause)
            ): count
            for cause, count in self.deaths_by_cause.items()
        }
        return {
            "tick": self.tick,
            "population": self.population,
            "born": self.born,
            "died": self.died,
            "deaths": deaths,
            "total_energy": self.total_energy,
            "total_resource": self.total_resource,
        }