"""World 测试：装配、确定性、随机可通行格、再生推进。"""
from __future__ import annotations

import numpy as np
import pytest

from simulation.config import SimConfig
from world.world import World


def make_world(seed: int = 42, **overrides) -> World:
    cfg = SimConfig(seed=seed, **overrides)
    return World(cfg, np.random.default_rng(cfg.seed))


def test_assembly_matches_config():
    w = make_world(world={"width": 32, "height": 24})
    assert w.width == 32 and w.height == 24
    assert w.resources.snapshot().shape == (24, 32)
    assert w.total_resource() == pytest.approx(w.resources.total())


def test_identical_seed_identical_world():
    a, b = make_world(seed=7), make_world(seed=7)
    assert np.array_equal(a.resources.snapshot(), b.resources.snapshot())
    c = make_world(seed=8)
    assert not np.array_equal(a.resources.snapshot(), c.resources.snapshot())


def test_random_passable_cell_within_bounds():
    w = make_world()
    rng = np.random.default_rng(0)
    for _ in range(100):
        x, y = w.random_passable_cell(rng)
        assert 0 <= x < w.width and 0 <= y < w.height
        assert w.terrain.is_passable(x, y)


def test_tick_regrowth_increases_total():
    w = make_world()
    before = w.total_resource()
    capacity = w.width * w.height * w.resources.capacity
    for _ in range(50):
        w.tick_regrowth()
    after = w.total_resource()
    assert before < after <= capacity + 1e-9


def test_resource_snapshot_is_copy():
    w = make_world()
    snap = w.resource_snapshot()
    snap[:, :] = 0.0
    assert w.total_resource() > 0.0