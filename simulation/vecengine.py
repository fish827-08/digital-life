"""VecEngine：数组化（Struct-of-Arrays）高速引擎 —— 与 SimulationEngine 规则等价。

设计动机（原则 7 的量级性能落地）：
- SimulationEngine 是"对象引擎"（AoS：dict[id → Organism]），每个 tick 对
  每个个体做 Python 级调用 → 百万 tick 级长程实验（如 1 万代 ≈ 1,400 万
  tick）耗时数小时；
- VecEngine 把全部存活血统改为定长 NumPy 数组（位置 x/y、能量、基因矩阵、
  年龄、世代、亲代），每个 tick 的代谢/进食/移动/衰老/死亡/繁殖全部批量
  向量化 → 单核 CPU 即可获得 5~20× 提速，未来可平移 CuPy 上 GPU。

规则等价性（与对象引擎的语义对齐，逐条说明）：
  1) 顺序契约不变：资源再生 → 种群行动（含 RNG 消费）；
  2) 个体行为不变：代谢 → 进食（仅对自己的格子）→ 概率移动 → 年龄推进；
     能量 ≤0 跳过进食/移动/年龄（同 Organism.step 的 early-return）；
  3) 死亡判定不变：先饿死（energy<=0）后老死（age>=life_span）；
  4) 繁殖不变：存活且 energy >= repro_fraction×max_energy，种群 < max_count
     才生育；子代能量 = 亲代能量对半，出生在亲代格，世代+1，记录亲代；
  5) RNG 调用顺序固定（同一种子 → 逐 tick 逐样本完全复现）。

已知的刻意差异（保证向量化的代价，全部是"统计等价"而非"逐位一致"）：
  a) 同一格多点同时取食改用"均分封顶"：每格总消耗 = min(存量, cap×数量)，
     与消费顺序无关（对象引擎是先到先得）。聚合守恒、确定性更强；
  b) 移动方向改为从 8 方向均匀抽签（对象引擎是逐次抽 (dx,dy) 直到非零），
     分布相同、RNG 流不同；
  c) 随机数流整体与对象引擎不同（批量采样 vs 逐个体采样）→ 两种引擎用同
     一种子不会逐位一致，但同规则、同分布，长期统计一致（有等价性测试）。

持久化/观测接口与 SimulationEngine 对齐（duck-typed）：
  tick / step() / run() / finished / extinct / history / total_born /
  total_died / death_cause_totals() / population{max_generation,
  alive_count, total_energy, organisms()} / world —— EvolutionObserver 与
  ExperimentRunner 无需改动即可挂载（observatory 只依赖这些表面）。
"""
from __future__ import annotations

import os
from collections import Counter
from typing import Optional

import numpy as np

from core.genome import Genome
from core.lifecycle import DeathCause, Lifecycle
from core.organism import Organism
from simulation.config import SimConfig
from simulation.tick import TickStats
from world.world import World

# 8 邻格方向表（索引 0..7；分布 = 均匀 8 邻，与对象引擎的
# "非零 (dx,dy) 均匀" 一致）
_DIR_DX = np.array([-1, 0, 1, -1, 1, -1, 0, 1], dtype=np.int64)
_DIR_DY = np.array([-1, -1, -1, 0, 0, 1, 1, 1], dtype=np.int64)


class VecPopulationView:
    """VecEngine 对演化/观测层暴露的种群视图（接口对齐对象 Population）。"""

    def __init__(self, engine: "VecEngine") -> None:
        self._engine = engine

    @property
    def max_generation(self) -> int:
        return self._engine._max_generation

    def alive_count(self) -> int:
        return len(self._engine._id)

    def total_energy(self) -> float:
        return float(self._engine._energy.sum())

    def organisms(self) -> list[Organism]:
        """按数组状态重建 Organism 对象列表（供 statistics.py 纯函数聚合）。

        仅观测采样时调用（约每百 tick 一次），不进入热路径。
        """
        eng = self._engine
        cfg = eng.config.organisms
        n = len(eng._id)
        out: list[Organism] = []
        for i in range(n):
            out.append(
                Organism(
                    organism_id=int(eng._id[i]),
                    x=int(eng._x[i]),
                    y=int(eng._y[i]),
                    genome=Genome(eng._genes[i].copy()),
                    config=cfg,
                    energy=float(eng._energy[i]),
                    lifecycle=Lifecycle(initial_age=int(eng._age[i])),
                    generation=int(eng._generation[i]),
                    parent_id=None if eng._parent[i] < 0 else int(eng._parent[i]),
                )
            )
        return out


class VecEngine:
    """数组化引擎（规则等价 SimulationEngine，见模块 docstring）。"""

    def __init__(self, config: SimConfig) -> None:
        self.config = config
        self.rng = np.random.default_rng(config.seed)
        self.world = World(config, self.rng)
        self.population = VecPopulationView(self)

        # ---- 存活血统 SoA 数组（alive rows == 全长） ----
        n = config.population.initial_count
        self._id: np.ndarray = np.arange(n, dtype=np.int64) - n  # 占位，下方重铺
        self._x = np.zeros(n, dtype=np.int64)
        self._y = np.zeros(n, dtype=np.int64)
        self._energy = np.full(n, config.organisms.initial_energy, dtype=np.float64)
        self._genes = np.empty((n, config.genome.gene_count), dtype=np.float64)
        self._age = np.zeros(n, dtype=np.int64)
        self._generation = np.zeros(n, dtype=np.int64)
        self._parent = np.full(n, -1, dtype=np.int64)
        self._next_id = 0
        self._max_generation = 0
        self.spawn_report_born = n
        self._spawn_initial()

        # ---- 运行期账本 ----
        self._tick = 0
        self._history: list[TickStats] = []
        self._history_limit = config.simulation.history_limit
        self._run_born = 0
        self._run_died = 0
        self._run_deaths: Counter = Counter()
        self._extinct = False
        self._finished = False

    # ---- 初始化 --------------------------------------------------------

    def _spawn_initial(self) -> None:
        cfg, wcfg = self.config.population, self.config.world
        n = cfg.initial_count
        # 与对象引擎一致的构造顺序：World(rng) 先铺资源，这里才用 rng。
        # 出生点：随机格（v1 无地形障碍，一次成功）。
        self._x = self.rng.integers(0, wcfg.width, size=n).astype(np.int64)
        self._y = self.rng.integers(0, wcfg.height, size=n).astype(np.int64)
        self._genes = self.rng.uniform(
            self.config.genome.gene_min,
            self.config.genome.gene_max,
            size=(n, self.config.genome.gene_count),
        )
        self._id = np.arange(self._next_id, self._next_id + n, dtype=np.int64)
        self._next_id += n

    # ---- 只读状态（对齐 SimulationEngine） -----------------------------

    @property
    def tick(self) -> int:
        return self._tick

    @property
    def history(self) -> list[TickStats]:
        return self._history

    @property
    def extinct(self) -> bool:
        return self._extinct

    @property
    def finished(self) -> bool:
        return self._finished

    @property
    def total_born(self) -> int:
        if self._history_limit > 0:
            return self.spawn_report_born + self._run_born
        return self.spawn_report_born + sum(s.born for s in self._history)

    @property
    def total_died(self) -> int:
        if self._history_limit > 0:
            return self._run_died
        return sum(s.died for s in self._history)

    def death_cause_totals(self) -> Counter:
        if self._history_limit > 0:
            return self._run_deaths.copy()
        totals: Counter = Counter()
        for s in self._history:
            totals.update(s.deaths_by_cause)
        return totals

    # ---- 推进 ----------------------------------------------------------

    def step(self) -> TickStats:
        """推进一个 tick，返回该 tick 的统计快照（对齐 SimulationEngine）。"""
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
        limit = self.config.simulation.ticks if ticks is None else ticks
        while not self._finished and self._tick < limit:
            self.step()
        return list(self._history)

    # ---- 内部：单 tick 向量化推进 ---------------------------------------

    def _advance_one_tick(self) -> TickStats:
        # 顺序契约（与 SimulationEngine 完全一致）：先资源再生，再种群行动。
        self.world.tick_regrowth()
        born, died, deaths = self._step_population()
        stats = TickStats(
            tick=self._tick,
            population=len(self._id),
            born=born,
            died=died,
            deaths_by_cause=deaths,
            total_energy=self.population.total_energy(),
            total_resource=self.world.total_resource(),
        )
        self._history.append(stats)
        if self._history_limit > 0:
            self._run_born += born
            self._run_died += died
            self._run_deaths.update(deaths)
            overflow = len(self._history) - self._history_limit
            if overflow > 0:
                del self._history[:overflow]
        return stats

    def _end_condition_met(self) -> bool:
        if self._extinct and self.config.simulation.stop_on_extinction:
            return True
        return self._tick >= self.config.simulation.ticks

    def _step_population(self) -> tuple[int, int, Counter]:
        """批量执行：行动 → 死亡 → 繁殖 → 清理。返回 (born, died, deaths)。"""
        ocfg, gcfg = self.config.organisms, self.config.genome
        P = len(self._id)
        if P == 0:
            return 0, 0, Counter()
        W, H = self.world.width, self.world.height

        genes = self._genes[:P]
        energy = self._energy[:P]

        # 1) 代谢（代谢倍率 = 0.5 + g1×1.5，见 TRAIT_TABLE 线性映射）
        metab_mult = 0.5 + genes[:, 1] * 1.5
        energy -= ocfg.base_metabolism * metab_mult
        alive = energy > 0.0

        # 2) 进食（仅对存活者）：每格均分封顶，聚合守恒
        if alive.any():
            idx = np.flatnonzero(alive)
            flat = self._y[idx] * W + self._x[idx]
            taken = self.world.resources.consume_at_flat(flat, ocfg.eat_amount)
            energy[idx] = np.minimum(
                ocfg.max_energy, energy[idx] + taken * ocfg.eat_efficiency
            )

        # 3) 移动：move_prob = g0；能量够 move_cost 才动
        moved = self.rng.random(P) < genes[:, 0]
        moved &= energy >= ocfg.move_cost
        Nm = int(moved.sum())
        if Nm:
            mi = np.flatnonzero(moved)
            d = self.rng.integers(0, 8, size=Nm)
            self._x[mi] = (self._x[mi] + _DIR_DX[d]) % W
            self._y[mi] = (self._y[mi] + _DIR_DY[d]) % H
            energy[mi] -= ocfg.move_cost

        # 4) 年龄推进（仅对存活者；饿死/代谢清零者不推进，同对象引擎）
        self._age[:P] += alive.astype(np.int64)

        # 5) 死亡判定：先饿死（energy<=0），后老死（age >= life_span）
        #    life_span = 200 + g3×3800
        starved = energy <= 0.0
        life_span = 200.0 + genes[:, 3] * 3800.0
        expired = (~starved) & (self._age[:P].astype(np.float64) >= life_span)
        dead = starved | expired
        deaths: Counter = Counter()
        n_starved = int(starved.sum())
        n_expired = int(expired.sum())
        if n_starved:
            deaths[DeathCause.STARVATION] = n_starved
        if n_expired:
            deaths[DeathCause.OLD_AGE] = n_expired

        # 6) 繁殖：存活且能量 >= repro_fraction×max_energy（repro_fraction = 0.25+g2×0.65），
        #    种群未达 max_count；先到先得（行序），子代本 tick 不行动。
        repro_thr = (0.25 + genes[:, 2] * 0.65) * ocfg.max_energy
        repro = (~dead) & (energy >= repro_thr)
        K = min(int(repro.sum()), self.config.population.max_count - P)
        born = 0
        if K > 0:
            ri = np.flatnonzero(repro)[:K]
            child_genes = self._genes[ri].copy()
            mut = self.rng.random((K, gcfg.gene_count)) < gcfg.mutation_rate
            if mut.any():
                sigma = gcfg.mutation_sigma * (gcfg.gene_max - gcfg.gene_min)
                noise = self.rng.normal(0.0, sigma, size=(K, gcfg.gene_count))
                child_genes = np.clip(
                    child_genes + np.where(mut, noise, 0.0),
                    gcfg.gene_min,
                    gcfg.gene_max,
                )
            child_energy = energy[ri] / 2.0
            energy[ri] -= child_energy

            ids = np.arange(self._next_id, self._next_id + K, dtype=np.int64)
            self._next_id += K
            self._id = np.concatenate([self._id, ids])
            self._x = np.concatenate([self._x, self._x[ri]])
            self._y = np.concatenate([self._y, self._y[ri]])
            self._energy = np.concatenate([self._energy, child_energy])
            self._genes = np.concatenate([self._genes, child_genes])
            self._age = np.concatenate([self._age, np.zeros(K, dtype=np.int64)])
            new_gen = self._generation[ri] + 1
            self._generation = np.concatenate([self._generation, new_gen])
            self._parent = np.concatenate([self._parent, self._id[ri]])
            born = K
            new_max = int(self._generation.max())
            if new_max > self._max_generation:
                self._max_generation = new_max

        # 7) 清理尸体（仅作用于本 tick 行动的旧行 [0:P]；子代不受影响）
        if dead.any():
            keep = ~dead
            n_tail = len(self._id) - P
            self._id = np.concatenate([self._id[:P][keep], self._id[P:]])
            self._x = np.concatenate([self._x[:P][keep], self._x[P:]])
            self._y = np.concatenate([self._y[:P][keep], self._y[P:]])
            self._energy = np.concatenate([self._energy[:P][keep], self._energy[P:]])
            self._genes = np.concatenate([self._genes[:P][keep], self._genes[P:]])
            self._age = np.concatenate([self._age[:P][keep], self._age[P:]])
            self._generation = np.concatenate(
                [self._generation[:P][keep], self._generation[P:]]
            )
            self._parent = np.concatenate([self._parent[:P][keep], self._parent[P:]])
            assert n_tail == 0 or len(keep) == P  # 保持不变量：mask 只覆盖旧行

        return born, n_starved + n_expired, Counter(deaths)