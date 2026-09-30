"""Panchanga times versus Swiss Ephemeris (oracle/generate_panchanga_fixtures.py).

The reference finds every event independently (rise and set with Swiss
Ephemeris' own routine; limb changes by bisection on its positions). Limb changes
are compared in TT, since Delta T for future dates is a prediction on which tools
differ by about a second. Every eighth case is run here; the accuracy report
covers all 560.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from jyotish_engine.astro.riseset import next_moonrise, next_moonset, next_sunrise, next_sunset
from jyotish_engine.astro.series import jd_ut_to_tt
from jyotish_engine.astro.time import Instant
from jyotish_engine.panchanga.elements import Limb
from jyotish_engine.panchanga.timing import all_limb_spans

FIXTURE = Path(__file__).parent / "fixtures" / "panchanga_swisseph.json"


def _cases() -> list[dict[str, Any]]:
    data: dict[str, Any] = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return list(data["cases"][::8])


CASES = _cases()


@pytest.mark.golden
@pytest.mark.parametrize("case", CASES, ids=[f"{c['city']}-{c['date']}" for c in CASES])
def test_rise_set_and_limb_changes(case: dict[str, Any]) -> None:
    lat, lon, elevation = case["latitude"], case["longitude"], case["elevation_m"]
    midnight = Instant.from_jd_ut(case["midnight_jd_ut"])
    sunrise = next_sunrise(midnight, lat, lon, elevation)
    assert sunrise is not None
    assert abs(sunrise.jd_ut - case["sunrise"]) * 86400 < 0.5
    sunset = next_sunset(sunrise, lat, lon, elevation)
    assert sunset is not None and abs(sunset.jd_ut - case["sunset"]) * 86400 < 0.5
    moonrise = next_moonrise(midnight, lat, lon, elevation)
    moonset = next_moonset(midnight, lat, lon, elevation)
    assert moonrise is not None and abs(moonrise.jd_ut - case["moonrise"]) * 86400 < 0.5
    assert moonset is not None and abs(moonset.jd_ut - case["moonset"]) * 86400 < 0.5

    spans = all_limb_spans(case["sunrise"], case["next_sunrise"])
    for limb in Limb:
        theirs = {
            (int(after), round(t + dt, 4)): t + dt for t, _, after, dt in case["changes"][limb]
        }
        for span in spans[limb]:
            ours_tt = float(jd_ut_to_tt([span.start_jd_ut])[0])
            matches = [t for (index, _), t in theirs.items() if index == span.index]
            assert matches, (limb, span.index)
            assert min(abs(ours_tt - t) for t in matches) * 86400 < 0.5, (limb, span.index)
        # The spans cover the whole Hindu day without gaps.
        assert spans[limb][0].start_jd_ut <= case["sunrise"] < spans[limb][0].end_jd_ut
        assert spans[limb][-1].end_jd_ut >= case["next_sunrise"]
        for before, after in zip(spans[limb], spans[limb][1:], strict=False):
            assert before.end_jd_ut == after.start_jd_ut
