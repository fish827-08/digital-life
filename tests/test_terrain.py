"""TerrainField 测试：默认全通行、显式设置、越界报错。"""
from __future__ import annotations

import pytest

from world.terrain import TerrainField


def test_all_passable_by_default():
    t = TerrainField(8, 6)
    assert t.is_passable(0, 0)
    assert t.is_passable(7, 5)
    assert t.blocked_count() == 0


def test_set_passable_and_snapshot():
    t = TerrainField(8, 6)
    t.set_passable(3, 4, False)
    assert not t.is_passable(3, 4)
    snap = t.snapshot()
    assert not snap[4][3]  # grid[y][x]
    assert snap.sum() == 8 * 6 - 1


def test_out_of_bounds_raises_index_error():
    t = TerrainField(8, 6)
    with pytest.raises(IndexError):
        t.is_passable(8, 0)