"""SimulationEngine：最小闭环主循环 —— tick 驱动 + 确定性随机。

设计原因：
- 引擎是唯一"节拍器"。可复现性的物理保证 = 固定 RNG 调用顺序：
  同一配置 + 同一种子 → 逐 tick 完全相同的世界演化（原则 8）。
  构造顺序：World(用 rng 铺资源) → spawn_initial(用 rng 选出生点/
  生成初代基因组) → 每 tick 由 population.update 消费 rng。
- 每 tick 的顺序契约（不可随意调换，属于"规则"的一部分）：
    1) world.tick_regrowth()   —— 资源再生先于进食
    2) population.update(rng)  —— 个体行动/繁殖/死亡（内部消费 rng）
- 引擎不持有任何"生命规则"：个体行为、繁殖阈值、死因判定都在
  演化层/个体内部，引擎只负责按节拍驱动（原则 6）。
"""
from __future__ import annotations

from collections import Counter
from typing import Optional

import numpy as np

from evolution.population import Population
from simulation.config import SimConfig
from simulation.tick import TickStats
from world.world import World


class SimulationEngine:
    """由配置确定性构造并驱动的完整模拟。"""

    def __init__(self, config: SimConfig) -> None:
        self.config = config
        self.rng = np.random.default_rng(config.seed)
        self.world = World(config, self.rng)
        self.population = Population(config, self.world)
        self.spawn_report = self.population.spawn_initial(self.rng)

        self._tick = 0  # 已完成的 tick 数
        self._history: list[TickStats] = []
        self._extinct = False
        self._finished = False

    # ---- 只读状态 --------------------------------------------------------

    @property
    def tick(self) -> int:
        return self._tick

    @property
    def history(self) -> list[TickStats]:
        """全程统计（只读视图，勿修改；run/step 中持续追加）。"""
        return self._history

    @property
    def extinct(self) -> bool:
        return self._extinct

    @property
    def finished(self) -> bool:
        """是否已满足终止条件（跑满 tick 或灭绝提前停止）。"""
        return self._finished

    @property
    def total_born(self) -> int:
        return self.spawn_report.born + sum(s.born for s in self._history)

    @property
    def total_died(self) -> int:
        return sum(s.died for s in self._history)

    def death_cause_totals(self) -> Counter:
        """全部历史死亡按死因汇总（Counter[DeathCause]）。"""
        totals: Counter = Counter()
        for s in self._history:
            totals.update(s.deaths_by_cause)
        return totals

    # ---- 推进 ------------------------------------------------------------

    def step(self) -> TickStats:
        """推进一个 tick，返回该 tick 的统计快照。

        引擎结束后调用会抛出 RuntimeError（防越界误用）。
        """
        if self._finished:
            raise RuntimeError("模拟已结束，无法继续推进 step()")
        stats = self._advance_one_tick()
        self._tick += 1
        if stats.population == 0:
            self._extinct = True
        if self._end_condition_met():
            self._finished = True
        return stats

    def run(self, ticks: Optional[int] = None) -> list[TickStats]:
        """从当前状态一直推进到终止，返回完整历史。

        ticks 省略时按 config.simulation.ticks；传入更小的值时提前截断。
        """
        limit = self.config.simulation.ticks if ticks is None else ticks
        while not self._finished and self._tick < limit:
            self._advance_one_tick()
            self._tick += 1
            if not self._extinct and self._history[-1].population == 0:
                self._extinct = True
            if self._end_condition_met():
                self._finished = True
        return list(self._history)

    # ---- 内部 ------------------------------------------------------------

    def _advance_one_tick(self) -> TickStats:
        # 顺序契约：先世界再生，再种群行动（见模块 docstring）。
        self.world.tick_regrowth()
        report = self.population.update(self.rng)
        stats = TickStats(
            tick=self._tick,
            population=report.population,
            born=report.born,
            died=report.died,
            deaths_by_cause=report.deaths_by_cause,
            total_energy=self.population.total_energy(),
            total_resource=self.world.total_resource(),
        )
        self._history.append(stats)
        return stats

    def _end_condition_met(self) -> bool:
        if self._extinct and self.config.simulation.stop_on_extinction:
            return True
        return self._tick >= self.config.simulation.ticks