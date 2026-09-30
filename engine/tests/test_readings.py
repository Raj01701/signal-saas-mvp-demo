"""Natal readings: one result per placement, matching the chart's own positions."""

from __future__ import annotations

import importlib
import sys
from datetime import datetime
from pathlib import Path

import pytest

from jyotish_engine.astro.bodies import GRAHAS
from jyotish_engine.chart import compute_chart
from jyotish_engine.core.zodiac import SIGN_LORDS, Sign
from jyotish_engine.models import BirthInput, ChartResult, PlaceInput
from jyotish_engine.rules.readings import compute_readings

ROOT = Path(__file__).resolve().parents[2]
DELHI = PlaceInput(name="New Delhi", latitude=28.6139, longitude=77.2090)


@pytest.fixture(scope="module", params=[datetime(1990, 5, 17, 12, 0), datetime(1975, 1, 3, 4, 45)])
def chart(request: pytest.FixtureRequest) -> ChartResult:
    return compute_chart(BirthInput(local_datetime=request.param, place=DELHI))


def test_one_reading_per_placement(chart: ChartResult) -> None:
    out = compute_readings(chart)
    assert out.catalogue_size == 375
    categories = [r.category.value for r in out.readings]
    assert categories == (
        ["lagna", "nakshatra"]
        + ["planet_in_sign"] * 7
        + ["planet_in_house"] * 9
        + ["lord_in_house"] * 12
    )
    assert all(r.sources and r.evidence and r.status.value == "draft" for r in out.readings)


def test_readings_follow_the_chart(chart: ChartResult) -> None:
    ids = {r.id for r in compute_readings(chart).readings}
    lagna = chart.ascendant.sign
    assert f"lagna.{Sign(lagna).name.lower()}" in ids
    signs = {g.body: g.sign for g in chart.grahas if g.body in GRAHAS}
    for body, sign in signs.items():
        assert f"planet_in_house.{body.value}_h{(sign - lagna) % 12 + 1}" in ids
    for house in range(1, 13):
        lord = SIGN_LORDS[Sign((lagna + house - 1) % 12)]
        placed = (signs[lord] - lagna) % 12 + 1
        assert f"lord_in_house.l{house}_h{placed}" in ids


def test_generated_rule_files_are_current(monkeypatch: pytest.MonkeyPatch) -> None:
    """knowledge/natal/ is what scripts/generate_readings.py writes (re-run it after edits)."""
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    module = importlib.import_module("generate_readings")
    try:
        for name, build in module.FILES:
            text = (ROOT / "knowledge" / "natal" / name).read_text(encoding="utf-8")
            assert text == module.HEADER + module._dump(build()), name
    finally:
        sys.modules.pop("generate_readings", None)
        sys.modules.pop("generate_rule_families", None)
