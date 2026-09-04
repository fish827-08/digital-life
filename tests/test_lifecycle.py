"""Lifecycle 生命周期状态机测试。"""
from __future__ import annotations

import pytest

from core.lifecycle import DeathCause, Lifecycle


def test_starts_alive_at_age_zero():
    lc = Lifecycle()
    assert lc.alive
    assert lc.age == 0
    assert lc.death_cause is None


def test_advance_increments_age():
    lc = Lifecycle()
    lc.advance()
    lc.advance()
    assert lc.age == 2


def test_expired_when_age_reaches_span():
    lc = Lifecycle()
    for _ in range(200):
        lc.advance()
    assert lc.expired(200.0)


def test_not_expired_before_span():
    lc = Lifecycle(initial_age=199)
    assert not lc.expired(200.0)


def test_die_records_cause_and_duplicate_keeps_first():
    lc = Lifecycle()
    lc.die(DeathCause.STARVATION)
    assert not lc.alive
    assert lc.death_cause is DeathCause.STARVATION
    lc.die(DeathCause.OLD_AGE)  # 重复调用不再覆盖
    assert lc.death_cause is DeathCause.STARVATION


def test_advance_after_death_is_frozen():
    lc = Lifecycle(initial_age=5)
    lc.die(DeathCause.OLD_AGE)
    lc.advance()
    assert lc.age == 5  # 死亡后年龄冻结


def test_expired_false_when_dead():
    lc = Lifecycle()
    lc.die(DeathCause.STARVATION)
    assert not lc.expired(0.0)  # 已死 → 不算"因老而亡"


def test_negative_initial_age_rejected():
    with pytest.raises(ValueError):
        Lifecycle(initial_age=-1)