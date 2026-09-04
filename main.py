"""数字生命模拟入口（第一阶段：无头最小闭环 CLI）。

用法（在项目根目录 digital_life/ 下）：
    py -m main                    # 默认配置跑完（seed=42, 1000 tick）
    py -m main --ticks 5000       # 覆盖 tick 数
    py -m main --seed 7 --quiet   # 固定种子 + 只打印最终摘要
    py -m main --seed random      # 用系统熵（不可复现）
"""
from __future__ import annotations

import argparse
from collections import Counter

import numpy as np

from core.lifecycle import DeathCause
from simulation.config import SimConfig
from simulation.engine import SimulationEngine


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="main",
        description="可自主进化的数字生命生态系统 — 无头最小闭环",
    )
    parser.add_argument("--ticks", type=int, default=None, help="覆盖配置中的最大 tick 数")
    parser.add_argument(
        "--seed",
        type=str,
        default=None,
        help="覆盖配置中的随机种子；传 'random' 表示用系统熵",
    )
    parser.add_argument("--quiet", action="store_true", help="不打印逐段进度，只打印最终摘要")
    return parser.parse_args()


def _resolve_config(args: argparse.Namespace) -> SimConfig:
    cfg = SimConfig()
    if args.ticks is not None:
        cfg.simulation.ticks = args.ticks
    if args.seed == "random":
        cfg.seed = None
    elif args.seed is not None:
        cfg.seed = int(args.seed)
    return cfg


def _print_progress(engine: SimulationEngine) -> None:
    interval = engine.config.simulation.log_interval
    if interval <= 0:
        return
    for s in engine.history[::interval]:
        print(
            f"  tick {s.tick:>6d}  pop={s.population:>5d}  "
            f"born={s.born:>4d} died={s.died:>4d}  "
            f"energy={s.total_energy:9.1f}  resource={s.total_resource:9.1f}"
        )


def _print_summary(cfg: SimConfig, engine: SimulationEngine) -> None:
    deaths: Counter = engine.death_cause_totals()
    cause_str = ", ".join(
        f"{cause.value if isinstance(cause, DeathCause) else cause}={n}"
        for cause, n in deaths.most_common()
    ) or "无"
    max_pop = max((s.population for s in engine.history), default=0)
    status = "灭绝防护触发" if engine.extinct else "自然跑满"
    seed_text = str(cfg.seed) if cfg.seed is not None else "系统熵(不可复现)"
    print("\n=== 模拟结束 ===")
    print(f"  状态:      {status}（{len(engine.history)} ticks）")
    print(f"  种子:      {seed_text}")
    print(f"  最终种群:  {engine.population.alive_count()}")
    print(f"  最高种群:  {max_pop}")
    print(f"  总出生:    {engine.total_born}")
    print(f"  总死亡:    {engine.total_died}")
    print(f"  死亡构成:  {cause_str}")
    print(f"  能量存量:  {engine.population.total_energy():.1f}")
    print(f"  资源存量:  {engine.world.total_resource():.1f}"
          f" / {engine.world.width * engine.world.height * cfg.resources.capacity:.1f} 全满量")


def main() -> None:
    args = _parse_args()
    cfg = _resolve_config(args)
    np.random.default_rng(cfg.seed)  # 提前触发 seed 类型检查，尽早报错

    engine = SimulationEngine(cfg)
    print(
        f"digital_life v0.1.0 — 最小闭环启动  "
        f"{cfg.world.width}x{cfg.world.height} 世界, "
        f"初代 {cfg.population.initial_count} 个体, 最多 {cfg.simulation.ticks} ticks"
    )
    if not args.quiet:
        print(f"  tick {0:>6d}  pop={engine.population.alive_count():>5d}  （初代出生）")

    engine.run()
    if not args.quiet:
        _print_progress(engine)
    _print_summary(cfg, engine)


if __name__ == "__main__":
    main()