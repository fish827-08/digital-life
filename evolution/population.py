"""Population：种群容器 —— 出生、逐 tick 推进、死亡清理、规模上限。

设计原因：
- 个体以 dict[id → Organism] 存放（v1 的 AoS 布局）：插入顺序即
  确定性迭代顺序；种群量级上来后可整体换 SoA / 向量化（原则 7）；
- update() 是演化层对外的"每 tick 总账"：行动 → 繁殖 → 死亡，
  引擎只需按节拍驱动 world 与 population，不触碰实现细节（原则 6）；
- 子代出生在亲代所在格（v1 允许同格叠放；领地 / 碰撞规则留给
  生态位阶段，原则 9）。
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Iterable, Optional

import numpy as np

from core.genome import Genome
from core.lifecycle import DeathCause
from core.organism import Organism
from evolution import reproduction, selection
from simulation.config import SimConfig
from world.world import World


@dataclass
class PopulationReport:
    """一个 tick 的种群账本（统计与断言语义）。"""

    born: int = 0
    died: int = 0
    deaths_by_cause: Counter = field(default_factory=Counter)
    population: int = 0


class Population:
    """种群容器。由配置 + 世界确定性构造。"""

    def __init__(self, config: SimConfig, world: World) -> None:
        self.config = config
        self.world = world
        self._organisms: dict[int, Organism] = {}
        self._next_id = 0

    # ---- 出生 ------------------------------------------------------------

    def spawn_initial(self, rng: np.random.Generator) -> PopulationReport:
        """按配置数量在随机可通行格生成初代。"""
        report = PopulationReport()
        n = self.config.population.initial_count
        for _ in range(n):
            x, y = self.world.random_passable_cell(rng)
            genome = Genome.random(self.config.genome, rng)
            org = Organism(
                organism_id=self._alloc_id(),
                x=x,
                y=y,
                genome=genome,
                config=self.config.organisms,
            )
            self._organisms[org.organism_id] = org
        report.born = n
        report.population = len(self._organisms)
        return report

    # ---- 每 tick 推进 ------------------------------------------------------

    def update(self, rng: np.random.Generator) -> PopulationReport:
        """推进一个 tick：存活个体行动 → 繁殖/死亡判定 → 清理尸体。

        注意：本 tick 新生的子代不参与本次行动（下个 tick 才动）。
        """
        report = PopulationReport()
        env = self.world.environment
        max_count = self.config.population.max_count

        for org in list(self._organisms.values()):  # 快照：避免边迭代边新增
            org.step(env, rng)

            cause = selection.death_cause_of(org)
            if cause is not None:
                org.lifecycle.die(cause)
                continue

            if len(self._organisms) < max_count and selection.wants_to_reproduce(
                org, self.config.organisms
            ):
                off = reproduction.create_offspring(org, rng, self.config.genome)
                org.energy -= off.energy  # 能量对半支付
                child = Organism(
                    organism_id=self._alloc_id(),
                    x=org.x,
                    y=org.y,  # 子代出生在亲代所在格
                    genome=off.genome,
                    config=self.config.organisms,
                    energy=off.energy,
                )
                self._organisms[child.organism_id] = child
                report.born += 1

        report.deaths_by_cause, report.died = self._purge_dead()
        report.population = len(self._organisms)
        return report

    # ---- 查询 ---------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._organisms)

    def alive_count(self) -> int:
        return len(self._organisms)

    def organisms(self) -> Iterable[Organism]:
        """迭代全部存活个体（只读视图，勿在迭代中修改）。"""
        return self._organisms.values()

    def get(self, organism_id: int) -> Optional[Organism]:
        return self._organisms.get(organism_id)

    def total_energy(self) -> float:
        return sum(o.energy for o in self._organisms.values())

    # ---- 内部 ----------------------------------------------------------------

    def _alloc_id(self) -> int:
        oid = self._next_id
        self._next_id += 1
        return oid

    def _purge_dead(self) -> tuple[Counter, int]:
        """清除死亡个体，返回 (死因统计, 死亡数量)。"""
        deaths: Counter = Counter()
        dead_ids = [oid for oid, o in self._organisms.items() if not o.alive]
        for oid in dead_ids:
            org = self._organisms.pop(oid)
            if org.lifecycle.death_cause is not None:
                deaths[org.lifecycle.death_cause] += 1
        return deaths, len(dead_ids)