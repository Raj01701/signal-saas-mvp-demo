"""Golden tests: M2 Jyotish quantities versus PyJHora reference values.

PyJHora uses true (geometric) positions, Lahiri ayanamsa, true nodes and the Hindu
sunrise; the engine is configured the same way here. Where PyJHora departs from
the classical texts, the tests document it and compare only what both agree on:

* its co-lord strength rule counts the Lagna as a planet;
* its Pranapada ghati count treats a clock second as one tharparai (0.4 s);
* for night births it measures the upagraha parts from sunrise, and it places the
  lordless eighth part after Saturn rather than at the end of the sequence;
* it evaluates the Sun at sunrise with the timezone added twice (fixtures use UTC,
  which neutralises this).
"""

from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest

from jyotish_engine.astro.ayanamsa import Ayanamsa, true_ayanamsa
from jyotish_engine.astro.bodies import GRAHAS, Body
from jyotish_engine.astro.houses import chart_angles
from jyotish_engine.astro.positions import (
    NodeType,
    PositionType,
    angular_distance,
    tropical_positions,
)
from jyotish_engine.astro.time import Instant
from jyotish_engine.astro.vedic_day import vedic_day
from jyotish_engine.core.dignity import CO_LORDS, compound_relationship
from jyotish_engine.special import lagnas
from jyotish_engine.special.arudha import bhava_arudhas
from jyotish_engine.special.karakas import chara_karakas
from jyotish_engine.special.upagraha import (
    Upagraha,
    part_lords,
    sun_based_upagrahas,
    time_based_upagrahas,
)

FIXTURE = Path(__file__).parent / "fixtures" / "chart_pyjhora.json"
ORDER = list(GRAHAS)
ARCMIN = 1.0 / 60.0

pytestmark = pytest.mark.golden


@lru_cache(maxsize=1)
def cases() -> list[dict[str, Any]]:
    data: dict[str, Any] = json.loads(FIXTURE.read_text(encoding="utf-8"))
    result: list[dict[str, Any]] = data["cases"]
    return result


def reference_positions(case: dict[str, Any]) -> dict[Body, float]:
    return {ORDER[int(k)]: v for k, v in case["positions"].items() if k != "L"}


def ours(case: dict[str, Any]) -> tuple[Instant, dict[Body, float], float]:
    instant = Instant.from_jd_ut(case["jd_ut"])
    ayan = true_ayanamsa(instant, Ayanamsa.LAHIRI)
    positions = tropical_positions(instant, GRAHAS, NodeType.TRUE, PositionType.TRUE)
    sidereal = {b: (p.longitude - ayan) % 360.0 for b, p in positions.items()}
    ascendant = (chart_angles(instant, case["lat"], case["lon"]).ascendant - ayan) % 360.0
    return instant, sidereal, ascendant


def test_true_positions_match_reference() -> None:
    for case in cases():
        _, sidereal, ascendant = ours(case)
        ref = reference_positions(case)
        for body in ORDER:
            tolerance = 2.0 if body is Body.MOON else 0.5  # Moon: future Delta T models differ
            assert angular_distance(sidereal[body], ref[body]) * 3600 < tolerance, (
                case["id"],
                body,
            )
        assert angular_distance(ascendant, case["positions"]["L"]) * 3600 < 0.1


def test_chara_karakas() -> None:
    for case in cases():
        karakas = chara_karakas(reference_positions(case))
        assert [ORDER.index(b) for b in karakas.values()] == case["karakas"], case["id"]


def test_compound_relationships() -> None:
    for case in cases():
        ref = reference_positions(case)
        signs = {b: int(ref[b] // 30.0) for b in ORDER}
        for i, a in enumerate(ORDER):
            for j, b in enumerate(ORDER):
                if i != j:
                    got = int(compound_relationship(a, b, signs[a], signs[b]))
                    assert got == case["compound"][i][j], (case["id"], a, b)


def _lagna_joins_a_co_lord(case: dict[str, Any], ref: dict[Body, float]) -> bool:
    lagna_sign = int(case["positions"]["L"] // 30.0)
    co_lords = {body for pair in CO_LORDS.values() for body in pair}
    return any(int(ref[b] // 30.0) == lagna_sign for b in co_lords)


def test_bhava_arudhas() -> None:
    compared = 0
    for case in cases():
        ref = reference_positions(case)
        if _lagna_joins_a_co_lord(case, ref):
            continue
        compared += 1
        asc_sign = int(case["positions"]["L"] // 30.0)
        assert bhava_arudhas(asc_sign, ref) == case["arudhas"], case["id"]
    assert compared >= 70


def _day_and_sun_at_sunrise(case: dict[str, Any], instant: Instant) -> tuple[Any, float]:
    day = vedic_day(instant, case["lat"], case["lon"])
    assert day is not None
    ayan = true_ayanamsa(day.sunrise, Ayanamsa.LAHIRI)
    sun = tropical_positions(day.sunrise, [Body.SUN], NodeType.TRUE, PositionType.TRUE)[Body.SUN]
    return day, (sun.longitude - ayan) % 360.0


def test_time_lagnas_indu_and_sree() -> None:
    for case in cases():
        instant, sidereal, ascendant = ours(case)
        day, sun_at_sunrise = _day_and_sun_at_sunrise(case, instant)
        minutes = day.minutes_since_sunrise(instant)
        local_hours = case["local"][3] + case["local"][4] / 60.0
        # PyJHora uses the same civil day's sunrise even for births before it.
        if local_hours >= case["sunrise_local_hours"]:
            assert (
                angular_distance(lagnas.bhava_lagna(sun_at_sunrise, minutes), case["bhava_lagna"])
                < 0.2 * ARCMIN
            )
            assert (
                angular_distance(lagnas.hora_lagna(sun_at_sunrise, minutes), case["hora_lagna"])
                < 0.2 * ARCMIN
            )
            assert (
                angular_distance(lagnas.ghati_lagna(sun_at_sunrise, minutes), case["ghati_lagna"])
                < 0.3 * ARCMIN
            )
        assert (
            angular_distance(lagnas.indu_lagna(ascendant, sidereal[Body.MOON]), case["indu_lagna"])
            < 0.1 * ARCMIN
        )
        assert (
            angular_distance(lagnas.sree_lagna(ascendant, sidereal[Body.MOON]), case["sree_lagna"])
            < 1.0 * ARCMIN
        )


def _pyjhora_ghatis(minutes_since_sunrise: float) -> float:
    """Reproduce PyJHora's ghati count, which scores each second as one tharparai."""
    hours = minutes_since_sunrise / 60.0
    whole_hours = int(hours)
    minutes = (hours - whole_hours) * 60.0
    whole_minutes = int(minutes)
    seconds = round((minutes - whole_minutes) * 60.0)  # rounded, then carried
    if seconds == 60:
        seconds, whole_minutes = 0, whole_minutes + 1
    if whole_minutes == 60:
        whole_minutes, whole_hours = 0, whole_hours + 1
    tharparai = whole_hours * 9000 + whole_minutes * 150 + seconds
    return tharparai / 3600.0


def test_pranapada_formula() -> None:
    for case in cases():
        instant, sidereal, _ = ours(case)
        day, _ = _day_and_sun_at_sunrise(case, instant)
        ghatis = _pyjhora_ghatis(day.minutes_since_sunrise(instant))
        emulated = lagnas.pranapada(sidereal[Body.SUN], ghatis * 24.0)
        # One tharparai (0.4 s) moves Pranapada by 2 arcminutes.
        assert angular_distance(emulated, case["pranapada"]) < 3.0 * ARCMIN, case["id"]


def test_sun_based_upagrahas() -> None:
    names = {
        "dhuma": Upagraha.DHUMA,
        "vyatipaata": Upagraha.VYATIPATA,
        "parivesha": Upagraha.PARIVESHA,
        "indrachaapa": Upagraha.INDRACHAPA,
        "upaketu": Upagraha.UPAKETU,
    }
    for case in cases():
        values = sun_based_upagrahas(reference_positions(case)[Body.SUN])
        for key, upagraha in names.items():
            assert angular_distance(values[upagraha], case["solar_upagrahas"][key]) < 1e-6


def _pyjhora_part_index(weekday: int, ruler: Body) -> int:
    cycle = [*part_lords(0, night=False)]  # Sun..Saturn, None
    start = cycle.index(part_lords(weekday, night=False)[0])
    rotated = [cycle[(start + k) % 8] for k in range(8)]
    return rotated.index(ruler)


def test_time_based_upagrahas_for_day_births() -> None:
    rulers = {
        "kala": Body.SUN,
        "mrityu": Body.MARS,
        "yamaghantaka": Body.JUPITER,
        "gulika": Body.SATURN,
        "mandi": Body.SATURN,
    }
    compared = 0
    for case in cases():
        instant, _, _ = ours(case)
        day = vedic_day(instant, case["lat"], case["lon"])
        assert day is not None
        if not day.is_day(instant):
            continue  # PyJHora mis-measures night parts

        def ascendant_at(jd_ut: float, lat: float = case["lat"], lon: float = case["lon"]) -> float:
            moment = Instant.from_jd_ut(jd_ut)
            angles = chart_angles(moment, lat, lon)
            return (angles.ascendant - true_ayanamsa(moment, Ayanamsa.LAHIRI)) % 360.0

        values = time_based_upagrahas(day.frame(), instant.jd_ut, ascendant_at)
        for key, ruler in rulers.items():
            standard = part_lords(day.weekday, night=False).index(ruler)
            if _pyjhora_part_index(day.weekday, ruler) != standard:
                continue  # the two conventions put this ruler in different parts
            upagraha = Upagraha(key)
            compared += 1
            assert angular_distance(values[upagraha], case["time_upagrahas"][key]) < 1.0 * ARCMIN, (
                case["id"],
                key,
            )
    assert compared >= 100
    assert math.isfinite(compared)
