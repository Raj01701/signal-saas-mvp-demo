"""Golden tests: astronomy layer versus Swiss Ephemeris reference values.

Fixtures come from ``oracle/generate_astro_fixtures.py`` (412 cases, 1900-2050,
latitudes -60 to +78). Tolerances are the M1 acceptance criteria in
``docs/ROADMAP.md``. The engine is fed the same TT and UT1 instants as the reference,
so these tests isolate the astronomy from Delta T modelling, which is checked
separately.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest

from jyotish_engine.astro.ayanamsa import (
    EPOCH_SYSTEMS,
    STAR_SYSTEMS,
    Ayanamsa,
    mean_ayanamsa,
    true_ayanamsa,
)
from jyotish_engine.astro.bodies import EPHEMERIS_BODIES
from jyotish_engine.astro.houses import HouseSystem, chart_angles, quadrant_cusps
from jyotish_engine.astro.positions import (
    angular_distance,
    mean_node_position,
    tropical_positions,
    true_node_position,
)
from jyotish_engine.astro.riseset import SunriseDefinition, next_sunrise, next_sunset
from jyotish_engine.astro.time import Instant

FIXTURE = Path(__file__).parent / "fixtures" / "astro_swisseph.json"
ARCSEC = 1.0 / 3600.0

pytestmark = pytest.mark.golden


@lru_cache(maxsize=1)
def cases() -> list[dict[str, Any]]:
    data: dict[str, Any] = json.loads(FIXTURE.read_text(encoding="utf-8"))
    result: list[dict[str, Any]] = data["cases"]
    return result


def _instant(case: dict[str, Any]) -> Instant:
    return Instant(jd_ut=case["jd_ut"], jd_tt=case["jd_tt"])


def _fixture_key(system: Ayanamsa) -> str:
    return system.value.replace("chitra", "citra")


def test_planet_longitudes_and_speeds() -> None:
    worst: dict[str, float] = {}
    for case in cases():
        positions = tropical_positions(_instant(case), EPHEMERIS_BODIES)
        for body, position in positions.items():
            lon, lat, _, speed = case["positions_tropical"][body.value]
            error = angular_distance(position.longitude, lon) / ARCSEC
            worst[body.value] = max(worst.get(body.value, 0.0), error)
            assert abs(position.latitude - lat) < 1.0 * ARCSEC, (case["id"], body)
            assert abs(position.speed - speed) < 2e-4, (case["id"], body)
    for body, error in worst.items():
        assert error < 1.0, f'{body}: {error:.4f}" exceeds 1"'


def test_lunar_nodes() -> None:
    for case in cases():
        instant = _instant(case)
        mean = mean_node_position(instant)
        true = true_node_position(instant)
        ref_mean = case["positions_tropical"]["mean_node"][0]
        ref_true = case["positions_tropical"]["true_node"][0]
        assert angular_distance(mean.longitude, ref_mean) < 1.0 * ARCSEC, case["id"]
        assert angular_distance(true.longitude, ref_true) < 5.0 * ARCSEC, case["id"]


@pytest.mark.parametrize("system", list(EPOCH_SYSTEMS))
def test_epoch_ayanamsas(system: Ayanamsa) -> None:
    for case in cases()[::3]:
        instant = _instant(case)
        key = _fixture_key(system)
        assert abs(mean_ayanamsa(instant, system) - case["ayanamsa_mean"][key]) < 0.05 * ARCSEC
        assert abs(true_ayanamsa(instant, system) - case["ayanamsa_true"][key]) < 0.05 * ARCSEC


@pytest.mark.parametrize(
    ("system", "tolerance_arcsec"),
    [(Ayanamsa.TRUE_CHITRA, 0.1), (Ayanamsa.TRUE_PUSHYA, 0.1), (Ayanamsa.TRUE_REVATI, 0.35)],
)
def test_star_ayanamsas(system: Ayanamsa, tolerance_arcsec: float) -> None:
    assert system in STAR_SYSTEMS
    for case in cases()[::6]:
        instant = _instant(case)
        reference = case["ayanamsa_true"][_fixture_key(system)]
        assert (
            angular_distance(true_ayanamsa(instant, system), reference) < tolerance_arcsec * ARCSEC
        )


def test_lahiri_is_near_the_calendar_reform_committee_definition() -> None:
    # 23 deg 15 min 00.658 sec (with nutation) on 1956-03-21 0h TT.
    value = true_ayanamsa(Instant.from_jd_tt(2435553.5), Ayanamsa.LAHIRI)
    assert abs(value - (23 + 15 / 60 + 0.658 / 3600)) < 0.2 * ARCSEC


def test_angles_and_house_cusps() -> None:
    for case in cases():
        angles = chart_angles(Instant.from_jd_ut(case["jd_ut"]), case["lat"], case["lon"])
        houses = case["houses"]
        assert angular_distance(angles.ascendant, houses["ascendant"]) < 2.0 * ARCSEC, case["id"]
        assert angular_distance(angles.mc, houses["mc"]) < 2.0 * ARCSEC, case["id"]
        for name in ("placidus", "porphyry", "equal", "sripati"):
            reference = houses[name]
            result = quadrant_cusps(HouseSystem(name), angles)
            if not reference["ok"]:
                assert result.fallback, (case["id"], name)
                continue
            assert not result.fallback
            for ours, theirs in zip(result.cusps, reference["cusps"], strict=True):
                assert angular_distance(ours, theirs) < 2.0 * ARCSEC, (case["id"], name)


@pytest.mark.parametrize("definition", list(SunriseDefinition))
def test_sunrise_and_sunset(definition: SunriseDefinition) -> None:
    # Above ~60 degrees Swiss Ephemeris' own results depend on where its search starts
    # (e.g. case r081 at 62 N differs by 6 minutes but agrees with us to 0.05 s when
    # restarted closer to the event), so the 2 s criterion is checked below 60 degrees.
    for case in cases()[::5]:
        if abs(case["lat"]) >= 60.0:
            continue
        start = Instant.from_jd_ut(case["jd_ut"] - 0.5)
        args = (start, case["lat"], case["lon"], case["alt_m"], definition)
        for event, ours in (("rise", next_sunrise(*args)), ("set", next_sunset(*args))):
            theirs = case["sun_rise_set"][f"{definition.value}_{event}"]
            assert ours is not None and theirs is not None, (case["id"], event)
            assert abs(ours.jd_ut - theirs) * 86400.0 < 2.0, (case["id"], event)


def test_delta_t_close_to_reference_for_the_past() -> None:
    # Both follow IERS observations up to the present; predictions diverge later.
    for case in cases():
        if case["jd_ut"] > 2460000.0:  # after Feb 2023
            continue
        ours = Instant.from_jd_ut(case["jd_ut"]).delta_t_seconds
        assert abs(ours - case["delta_t_s"]) < 1.0, case["id"]
