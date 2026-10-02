"""Stability windows of the time-sensitive chart factors."""

from __future__ import annotations

from datetime import datetime

import pytest

from jyotish_engine.chart import compute_chart
from jyotish_engine.models import BirthInput, PlaceInput
from jyotish_engine.sensitivity import compute_sensitivity

DELHI = PlaceInput(name="New Delhi", latitude=28.6139, longitude=77.2090)


def test_windows_around_a_recent_sign_change() -> None:
    chart = compute_chart(BirthInput(local_datetime=datetime(1990, 5, 17, 12, 0), place=DELHI))
    result = {f.name: f for f in compute_sensitivity(chart).factors}
    lagna, d9, d60 = result["Lagna"], result["D9 lagna"], result["D60 lagna"]
    # The lagna entered Leo about 4 minutes earlier: every division changed with it.
    assert lagna.value == "sign 5" and lagna.minutes_before == pytest.approx(3.8, abs=0.1)
    assert d9.minutes_before == pytest.approx(lagna.minutes_before, abs=0.02)
    assert lagna.fragile and d9.fragile  # within the default 5-minute uncertainty
    # A D60 part lasts about two minutes; a navamsha about thirteen.
    assert (d60.minutes_before or 0) + (d60.minutes_after or 0) < 4.0
    assert 10.0 < (d9.minutes_before or 0) + (d9.minutes_after or 0) < 16.0
    moon = result["Moon nakshatra pada"]
    assert not moon.fragile and (moon.minutes_before or 0) > 60


def test_uncertainty_from_the_birth_record() -> None:
    birth = BirthInput(
        local_datetime=datetime(1990, 5, 17, 12, 30), place=DELHI, uncertainty_minutes=1.0
    )
    result = compute_sensitivity(compute_chart(birth))
    assert result.uncertainty_minutes == 1.0
    assert not {f.name: f for f in result.factors}["Lagna"].fragile
