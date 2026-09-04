"""Metabolism：能量收支规则（纯函数）。

设计原因（原则 6：避免把逻辑写死在单一类）：
- 把"能量如何进、如何出"从个体类中抽离为无状态纯函数，
  可单独测试、可复用、可被未来策略（如环境毒物、冬眠等）替换；
- 本模块不持有任何状态：入参是数值，出参是数值/净变化。
"""
from __future__ import annotations


def metabolic_consumption(base_metabolism: float, metabolism_mult: float) -> float:
    """单 tick 代谢消耗 = 基础代谢 × 基因决定的倍率。"""
    return base_metabolism * metabolism_mult


def feeding_gain(amount_eaten: float, eat_efficiency: float) -> float:
    """进食获得的能量 = 实际摄入量 × 转化效率。"""
    return amount_eaten * eat_efficiency


def clamp_energy(energy: float, max_energy: float) -> float:
    """把能量钳制到 [0, max_energy]（进食收益不得超过能量上限）。"""
    if energy < 0.0:
        return 0.0
    if energy > max_energy:
        return max_energy
    return energy