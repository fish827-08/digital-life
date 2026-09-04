"""Selection：选择压 —— v1 由能量经济学涌现，不预定义进化方向。

设计原因：
- "什么能被选择"即游戏规则：能赚到能量并尽早繁殖的个体留下来。
  本模块显式化两条选择压的判定：
    1) 繁殖门槛：能量 ≥ 基因决定的阈值（repro_fraction × max_energy）；
    2) 死亡判定：饿死（能量耗尽）/ 老死（寿命到限）。
- 之后若要换"适应度打分"、群体选择等机制，只改本模块（原则 4/6）。
"""
from __future__ import annotations

from typing import Optional

from core.lifecycle import DeathCause
from core.organism import Organism
from simulation.config import OrganismConfig


def wants_to_reproduce(organism: Organism, config: OrganismConfig) -> bool:
    """选择压之一：能量是否达到基因决定的繁殖阈值。"""
    threshold = organism.phenotype["repro_fraction"] * config.max_energy
    return organism.energy >= threshold


def death_cause_of(organism: Organism) -> Optional[DeathCause]:
    """选择压之二：判定个体本 tick 是否死亡，返回死因或 None。

    判定顺序固定（先饿死后老死），保证确定性（原则 8）。
    """
    if organism.is_starved():
        return DeathCause.STARVATION
    if organism.is_expired():
        return DeathCause.OLD_AGE
    return None