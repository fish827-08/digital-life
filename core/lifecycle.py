"""Lifecycle：个体生命周期（年龄推进、死亡判定、死因记录）。

设计原因：
- 生命周期是"时间性状态机"，与"能量/基因组"正交，单独成类，
  避免 Organism 面面俱到（原则 6）；
- 死亡判定规则（能量耗尽的饿死、年龄到限的老死）由引擎/演化层
  依据本类的查询方法执行，本类只负责记录与状态推进 —— 单一职责。
"""
from __future__ import annotations

from enum import Enum


class DeathCause(Enum):
    """死亡原因（第一阶段）。"""

    STARVATION = "starvation"  # 能量耗尽
    OLD_AGE = "old_age"  # 寿命到限


class Lifecycle:
    """个体生命周期。构造后可指定初始年龄（测试/存档恢复用）。"""

    __slots__ = ("_age", "_alive", "_death_cause")

    def __init__(self, initial_age: int = 0) -> None:
        if initial_age < 0:
            raise ValueError(f"初始年龄不能为负：{initial_age}")
        self._age = initial_age
        self._alive = True
        self._death_cause: DeathCause | None = None

    # ---- 只读查询 ------------------------------------------------------

    @property
    def age(self) -> int:
        return self._age

    @property
    def alive(self) -> bool:
        return self._alive

    @property
    def death_cause(self) -> DeathCause | None:
        return self._death_cause

    def expired(self, life_span: float) -> bool:
        """寿命判定：存活且年龄 ≥ 预定寿命（tick 数，可浮点）。"""
        return self._alive and self._age >= life_span

    # ---- 状态推进 ------------------------------------------------------

    def advance(self) -> None:
        """年龄 +1（仅对存活个体调用；死亡个体不再推进）。"""
        if self._alive:
            self._age += 1

    def die(self, cause: DeathCause) -> None:
        """标记死亡并记录死因；重复调用保持首次死因。"""
        if self._alive:
            self._alive = False
            self._death_cause = cause

    def __repr__(self) -> str:
        state = "alive" if self._alive else f"dead({self._death_cause.value})"
        return f"Lifecycle(age={self._age}, {state})"