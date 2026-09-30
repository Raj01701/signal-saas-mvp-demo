"""Golden tests: sidereal ingresses and stations versus Swiss Ephemeris.

The reference bisects Swiss Ephemeris positions (Lahiri, apparent, true node) over
1995-2025 (the Moon over 1995-1996). Milestone target: ingress times within one
minute; the engine is within about a second.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest

from jyotish_engine.astro.bodies import Body
from jyotish_engine.transit.search import Motion, sign_ingresses, stations

FIXTURE = Path(__file__).parent / "fixtures" / "transits_swisseph.json"

pytestmark = pytest.mark.golden

INGRESS_TOLERANCE_S = 20.0  # the true node moves slowly; planets agree within 1 s
STATION_TOLERANCE_S = 5.0


@lru_cache(maxsize=1)
def data() -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return loaded


@pytest.mark.parametrize(
    "name", ["sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn", "rahu"]
)
def test_sign_ingresses(name: str) -> None:
    reference = data()["bodies"][name]
    ours = sign_ingresses(Body(name), reference["start"], reference["end"])
    theirs = reference["ingresses"]
    assert len(ours) == len(theirs)
    for event, (jd_ut, from_sign, to_sign) in zip(ours, theirs, strict=True):
        assert (event.from_index, event.to_index) == (from_sign, to_sign)
        assert abs(event.jd_ut - jd_ut) * 86400.0 < INGRESS_TOLERANCE_S, (name, jd_ut)
        forward = (to_sign - from_sign) % 12 == 1
        assert (event.motion is Motion.DIRECT) == forward


@pytest.mark.parametrize("name", ["mars", "mercury", "jupiter", "venus", "saturn"])
def test_stations(name: str) -> None:
    reference = data()["bodies"][name]
    ours = stations(Body(name), reference["start"], reference["end"])
    theirs = reference["stations"]
    assert len(ours) == len(theirs)
    for event, (jd_ut, longitude, turn) in zip(ours, theirs, strict=True):
        assert abs(event.jd_ut - jd_ut) * 86400.0 < STATION_TOLERANCE_S, (name, jd_ut)
        assert abs((event.longitude - longitude + 180.0) % 360.0 - 180.0) < 1.0 / 3600.0
        assert (event.motion is Motion.DIRECT) == (turn == 1)


def test_nodes_and_luminaries_do_not_station() -> None:
    for body in (Body.SUN, Body.MOON, Body.RAHU, Body.KETU):
        assert stations(body, 2451545.0, 2451545.0 + 400.0) == []
