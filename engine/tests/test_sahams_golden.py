"""Tajika sahams versus PyJHora on random positions (oracle/generate_saham_fixtures.py).

Both follow P.V.R. Narasimha Rao's table of 36 sahams. PyJHora departs from it in
three ways, which the test recognises case by case and reproduces exactly, so that
every remaining value must match ours:

* house cusps (lagna + (n - 1) x 30 degrees) are not reduced below 360, so its
  "is C between B and A" test misreads their sign;
* it takes Rahu or Ketu as the lord of Aquarius or Scorpio when they are stronger,
  where Tajika uses Saturn and Mars;
* it reverses Labha by night, although the table (and its own comment) says Labha is
  the same by day and night.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from jyotish_engine.annual.sahams import RULES, between, compute_sahams, saham_longitude
from jyotish_engine.astro.bodies import Body

FIXTURE = Path(__file__).parent / "fixtures" / "sahams_pyjhora.json"
LORDS = [
    "mars", "venus", "mercury", "moon", "sun", "mercury",
    "venus", "mars", "jupiter", "saturn", "saturn", "jupiter",
]  # fmt: skip
#: Sahams using a house cusp: name -> (house, whether the cusp is term A or C).
HOUSE_SAHAMS = {
    "paradesa": (9, "a"),
    "artha": (2, "a"),
    "mrityu": (8, "a"),
    "apamrityu": (8, "a"),
    "labha": (11, "a"),
    "santapa": (6, "c"),
}
#: Sahams using the lord of a house.
LORD_SAHAMS = {"samartha": 1, "paradesa": 9, "artha": 2, "labha": 11}


def _cases() -> list[dict[str, Any]]:
    data: dict[str, Any] = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return list(data["cases"])


def _close(a: float, b: float) -> bool:
    return abs((a - b + 180.0) % 360.0 - 180.0) < 1e-7


def _pyjhora_lord(case: dict[str, Any], sign: int) -> str:
    if sign == 7:
        return str(case["lords"]["scorpio"])
    if sign == 10:
        return str(case["lords"]["aquarius"])
    return LORDS[sign]


def _pyjhora_between(a: float, b: float, c: float) -> bool:
    """PyJHora's test, with signs taken from unreduced longitudes."""
    sign_a, sign_b, sign_c = int(a // 30), int(b // 30), int(c // 30)
    for n in range(sign_b, sign_b + 11):
        following = (n + 1) % 12
        if following == sign_c:
            return True
        if following == sign_a:
            return False
    return False


def _pyjhora_saham(a: float, b: float, c: float) -> float:
    value = a - b + c
    if not _pyjhora_between(a, b, c):
        value += 30.0
    return value % 360.0


def _quirk(case: dict[str, Any], name: str) -> bool:
    """Whether one of PyJHora's three departures affects this saham in this case."""
    lagna, night = case["lagna"], case["night"]
    if name == "labha" and night:
        return True
    if name in HOUSE_SAHAMS and lagna + (HOUSE_SAHAMS[name][0] - 1) * 30.0 >= 360.0:
        return True
    signs: list[int] = []
    if name in LORD_SAHAMS:
        signs.append(int((lagna + (LORD_SAHAMS[name] - 1) * 30.0) % 360.0 // 30))
    if name == "karyasiddhi":
        signs.append(int(case["planets"]["moon" if night else "sun"] // 30))
    return any(_pyjhora_lord(case, s) != LORDS[s] for s in signs)


def _pyjhora_variant(case: dict[str, Any], name: str) -> float:
    """The saham as PyJHora computes it, departures included."""
    lagna, night, lon = case["lagna"], case["night"], case["planets"]

    def lord_lon(house: int) -> float:
        sign = int((lagna + (house - 1) * 30.0) % 360.0 // 30)
        return float(lon[_pyjhora_lord(case, sign)])

    if name in ("paradesa", "artha"):
        house = HOUSE_SAHAMS[name][0]
        return _pyjhora_saham(lagna + (house - 1) * 30.0, lord_lon(house), lagna)
    if name == "labha":
        cusp, lord = lagna + 300.0, lord_lon(11)
        return _pyjhora_saham(lord, cusp, lagna) if night else _pyjhora_saham(cusp, lord, lagna)
    if name == "mrityu":
        return _pyjhora_saham(lagna + 210.0, lon["moon"], lagna)
    if name == "apamrityu":
        cusp, mars = lagna + 210.0, lon["mars"]
        return _pyjhora_saham(mars, cusp, lagna) if night else _pyjhora_saham(cusp, mars, lagna)
    if name == "santapa":
        saturn, moon = lon["saturn"], lon["moon"]
        a, b = (moon, saturn) if night else (saturn, moon)
        return _pyjhora_saham(a, b, lagna + 150.0)
    if name == "samartha":
        lord = _pyjhora_lord(case, int(lagna // 30))
        a, b = ("jupiter", "mars") if lord == "mars" else ("mars", lord)
        if night:
            a, b = b, a
        return _pyjhora_saham(lon[a], lon[b], lagna)
    if name == "karyasiddhi":
        moving = "moon" if night else "sun"
        lord = _pyjhora_lord(case, int(lon[moving] // 30))
        return _pyjhora_saham(lon["saturn"], lon[moving], lon[lord])
    raise AssertionError(f"no PyJHora variant for {name}")


@pytest.mark.golden
def test_sahams_match_pyjhora() -> None:
    exact = explained = 0
    for case in _cases():
        sidereal = {Body(k): v for k, v in case["planets"].items()}
        ours = {
            s.name: s.longitude for s in compute_sahams(case["lagna"], sidereal, not case["night"])
        }
        assert set(ours) == set(case["sahams"])
        for name, theirs in case["sahams"].items():
            if _quirk(case, name):
                assert _close(_pyjhora_variant(case, name), theirs), (case["id"], name)
                explained += 1
            else:
                assert _close(ours[name], theirs), (case["id"], name, ours[name], theirs)
                exact += 1
    assert exact / (exact + explained) > 0.85  # the departures stay the exception


def test_between_rule_and_correction() -> None:
    # B in Aries, A in Leo: Taurus to Leo lies on the way, Aries and Virgo do not.
    assert between(10.0, 130.0, 40.0)
    assert between(10.0, 130.0, 125.0)
    assert not between(10.0, 130.0, 5.0)
    assert not between(10.0, 130.0, 170.0)
    assert saham_longitude(130.0, 10.0, 40.0) == 160.0
    assert saham_longitude(130.0, 10.0, 170.0) == (130.0 - 10.0 + 170.0 + 30.0) % 360.0
    # C the same point as A (Roga): on the arc by definition.
    assert saham_longitude(50.0, 45.0, 50.0) == 55.0


def test_night_formulas_and_special_cases() -> None:
    sidereal = {b: 15.0 + 30.0 * i for i, b in enumerate(Body) if i < 9}
    by_day = {s.name: s.longitude for s in compute_sahams(0.0, sidereal, by_day=True)}
    by_night = {s.name: s.longitude for s in compute_sahams(0.0, sidereal, by_day=False)}
    for rule in RULES:
        if not rule.reverse_at_night and rule.night is None:
            assert by_day[rule.name] == by_night[rule.name], rule.name
    # Pitri and Rajya share one formula.
    assert by_day["pitri"] == by_day["rajya"] and by_night["pitri"] == by_night["rajya"]
    names = [r.name for r in RULES]
    assert len(names) == len(set(names)) == 36
    assert {r.name for r in RULES if r.sensitive} == {
        "roga", "mrityu", "paradara", "jadya", "bandhana", "apamrityu",
    }  # fmt: skip
