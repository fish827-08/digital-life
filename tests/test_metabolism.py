"""Metabolism 纯函数测试。"""
from __future__ import annotations

import pytest

from core.metabolism import clamp_energy, feeding_gain, metabolic_consumption


def test_metabolic_consumption():
    assert metabolic_consumption(1.0, 1.0) == pytest.approx(1.0)
    assert metabolic_consumption(1.0, 2.0) == pytest.approx(2.0)
    assert metabolic_consumption(0.5, 0.5) == pytest.approx(0.25)


def test_feeding_gain():
    assert feeding_gain(0.3, 2.0) == pytest.approx(0.6)
    assert feeding_gain(0.0, 2.0) == pytest.approx(0.0)


def test_clamp_energy_bounds():
    assert clamp_energy(-5.0, 100.0) == 0.0
    assert clamp_energy(50.0, 100.0) == 50.0
    assert clamp_energy(150.0, 100.0) == 100.0