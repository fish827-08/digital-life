"""ResourceField 测试：初始填充、消费、再生、快照、确定性。"""
from __future__ import annotations

import numpy as np
import pytest

from simulation.config import ResourceConfig
from world.resource import ResourceField


def make_field(rng=None, **overrides) -> ResourceField:
    cfg = ResourceConfig(**overrides)
    return ResourceField(16, 8, cfg, rng if rng is not None else np.random.default_rng(0))


def test_init_shape_and_bounds():
    f = make_field()
    assert f.width == 16 and f.height == 8
    snap = f.snapshot()
    assert snap.shape == (8, 16)  # grid[y][x]
    cap = ResourceConfig().capacity * ResourceConfig().initial_fill
    assert np.all((snap >= 0.0) & (snap <= cap))


def test_init_is_deterministic_with_seed():
    a = make_field(rng=np.random.default_rng(42))
    b = make_field(rng=np.random.default_rng(42))
    assert np.array_equal(a.snapshot(), b.snapshot())


def test_consume_reduces_and_returns_min():
    f = make_field()
    x, y = 3, 4
    before = f.amount_at(x, y)
    taken = f.consume(x, y, before * 0.4)
    assert taken == pytest.approx(before * 0.4)
    assert f.amount_at(x, y) == pytest.approx(before - taken)


def test_consume_capped_by_available():
    f = make_field()
    x, y = 3, 4
    before = f.amount_at(x, y)
    taken = f.consume(x, y, before + 100.0)
    assert taken == pytest.approx(before)
    assert f.amount_at(x, y) == 0.0


def test_consume_zero_when_empty():
    f = make_field()
    f.consume(1, 1, 1e9)
    assert f.consume(1, 1, 0.5) == 0.0


def test_regrow_increases_and_caps_at_capacity():
    f = make_field()
    f.consume(3, 4, f.amount_at(3, 4))  # 清空一格
    f.regrow()
    assert f.amount_at(3, 4) == pytest.approx(f.regrowth_rate)
    # 连跑足够多次后到达 capacity 上限
    for _ in range(10000):
        f.regrow()
    assert np.all(f.snapshot() <= f.capacity + 1e-9)
    assert f.amount_at(3, 4) == pytest.approx(f.capacity)


def test_regrow_never_exceeds_capacity_vectorized():
    f = make_field()
    f.regrow()
    assert np.all(f.snapshot() <= f.capacity + 1e-9)


def test_total_sums_grid():
    f = make_field()
    assert f.total() == pytest.approx(f.snapshot().sum())


def test_snapshot_is_copy():
    f = make_field()
    snap = f.snapshot()
    snap[0, 0] = -999.0
    assert f.amount_at(0, 0) != -999.0


def test_out_of_bounds_raises_index_error():
    f = make_field()
    with pytest.raises(IndexError):
        f.amount_at(f.width, 0)
    with pytest.raises(IndexError):
        f.consume(0, f.height, 1.0)