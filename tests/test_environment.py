"""Environment 测试：坐标包装、资源路由、邻格选择与地形尊重。"""
from __future__ import annotations

import numpy as np
import pytest

from simulation.config import ResourceConfig
from world.environment import Environment
from world.resource import ResourceField
from world.terrain import TerrainField

W, H = 16, 8


def make_env(wrap: bool = True, terrain=None, rng=None) -> Environment:
    rr = ResourceField(W, H, ResourceConfig(), rng if rng is not None else np.random.default_rng(0))
    tt = terrain if terrain is not None else TerrainField(W, H)
    return Environment(W, H, wrap, rr, tt)


# ---- 坐标包装 -----------------------------------------------------------


def test_wrap_resource_at_negative():
    env = make_env(wrap=True)
    assert env.resource_at(-1, 0) == env.resource_at(W - 1, 0)


def test_wrap_consume_routes_to_wrapped_cell():
    env = make_env(wrap=True)
    before = env.resource_at(W - 1, 3)
    env.consume_resource(-1, 3, before)
    assert env.resource_at(W - 1, 3) == pytest.approx(0.0)
    assert env.resource_at(0, 3) > 0.0  # 没有动到另一侧的格子


def test_nowrap_out_of_bounds_raises():
    env = make_env(wrap=False)
    with pytest.raises(IndexError):
        env.resource_at(-1, 0)
    with pytest.raises(IndexError):
        env.consume_resource(0, H, 1.0)


# ---- 邻格选择 -----------------------------------------------------------


def test_random_neighbor_returns_adjacent_cell():
    env = make_env(wrap=False)
    rng = np.random.default_rng(0)
    seen = set()
    for _ in range(50):
        nx, ny = env.random_neighbor(5, 5, rng)
        assert (nx, ny) != (5, 5)  # 全通地形下必然移动
        assert abs(nx - 5) <= 1 and abs(ny - 5) <= 1
        seen.add((nx, ny))
    assert len(seen) > 1  # 不是固定方向


def test_random_neighbor_wrap_stays_in_bounds_at_edge():
    env = make_env(wrap=True)
    rng = np.random.default_rng(0)
    for _ in range(50):
        nx, ny = env.random_neighbor(0, 0, rng)
        assert 0 <= nx < W and 0 <= ny < H


def test_random_neighbor_nowrap_never_out_of_bounds():
    env = make_env(wrap=False)
    rng = np.random.default_rng(0)
    for _ in range(200):
        nx, ny = env.random_neighbor(0, 0, rng)  # 角落出发
        assert 0 <= nx < W and 0 <= ny < H


def test_random_neighbor_respects_terrain():
    t = TerrainField(W, H)
    env = make_env(wrap=False, terrain=t)
    rng = np.random.default_rng(0)
    for _ in range(50):
        nx, ny = env.random_neighbor(5, 5, rng)
        assert env.terrain.is_passable(nx, ny)


def test_random_neighbor_stays_when_fully_blocked():
    t = TerrainField(W, H)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            t.set_passable(5 + dx, 5 + dy, False)
    env = make_env(wrap=False, terrain=t)
    rng = np.random.default_rng(0)
    assert env.random_neighbor(5, 5, rng) == (5, 5)  # 重试耗尽 → 原地不动


def test_random_neighbor_deterministic():
    env = make_env(wrap=True)
    r1 = env.random_neighbor(4, 4, np.random.default_rng(7))
    r2 = env.random_neighbor(4, 4, np.random.default_rng(7))
    assert r1 == r2