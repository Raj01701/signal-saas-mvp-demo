"""Golden tests: nakshatra dashas versus PyJHora, given the same Moon longitude.

PyJHora converts dasha years to days with the "true sidereal year" around the
birth. The fixture records the year it used, and the dasha arithmetic is compared
using that same year. The engine's own true sidereal year is compared with an
exact Swiss Ephemeris bisection instead, because PyJHora's sankranti interpolation
is sometimes a few minutes off.

Every period's lords and start time must match to within a second. PyJHora divides
antardashas equally for every system except Vimshottari and Ashtottari, whereas
BPHS divides them in proportion to the lords' years (the engine's default). The
comparison uses the rule the reference applies.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest

from jyotish_engine.astro.bodies import GRAHAS
from jyotish_engine.astro.positions import PositionType
from jyotish_engine.dasha.base import Period, SubPeriodRule
from jyotish_engine.dasha.conditions import applicability
from jyotish_engine.dasha.nakshatra import NakshatraDasha, mahadashas, sub_periods
from jyotish_engine.dasha.years import true_sidereal_year_days
from jyotish_engine.settings import Settings

FIXTURE = Path(__file__).parent / "fixtures" / "dashas_pyjhora.json"
ORDER = list(GRAHAS)
ONE_SECOND = 1.0 / 86400.0

pytestmark = pytest.mark.golden

REFERENCE_RULE = {
    NakshatraDasha.VIMSHOTTARI: SubPeriodRule.PROPORTIONAL,
    NakshatraDasha.ASHTOTTARI: SubPeriodRule.PROPORTIONAL,
}


@lru_cache(maxsize=1)
def data() -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return loaded


def _flatten(periods: list[Period], system: NakshatraDasha, depth: int) -> list[Period]:
    if depth == 1:
        return periods
    rule = REFERENCE_RULE.get(system, SubPeriodRule.EQUAL)
    out: list[Period] = []
    for period in periods:
        out += _flatten(sub_periods(system, period, rule), system, depth - 1)
    return out


def _compare(case: dict[str, Any], system: NakshatraDasha, key: str, depth: int) -> None:
    rows = case["systems"][key]
    periods = mahadashas(system, case["jd_ut"], case["moon"], case["year_days"], cycles=3)
    ours = _flatten(periods, system, depth)
    assert len(ours) >= len(rows)
    for period, (lords, offset) in zip(ours, rows, strict=False):
        assert [ORDER.index(b) for b in period.lords] == lords, (case["id"], system)
        start = case["jd_ut"] + offset
        assert abs(period.start_jd - start) < ONE_SECOND, (case["id"], system, lords)


@pytest.mark.parametrize("system", list(NakshatraDasha))
def test_mahadashas_and_antardashas(system: NakshatraDasha) -> None:
    for case in data()["cases"]:
        _compare(case, system, system.value, depth=2)


def test_vimshottari_pratyantardashas() -> None:
    cases = [c for c in data()["cases"] if "vimshottari_level3" in c["systems"]]
    assert cases
    for case in cases:
        _compare(case, NakshatraDasha.VIMSHOTTARI, "vimshottari_level3", depth=3)


def test_true_sidereal_year() -> None:
    """Mesha sankranti to Mesha sankranti, versus exact Swiss Ephemeris bisection."""
    settings = Settings(position_type=PositionType.TRUE)
    for case in data()["cases"][:12]:
        ours = true_sidereal_year_days(case["jd_ut"], settings)
        assert abs(ours - case["true_sidereal_year_days"]) * 86400.0 < 0.5, case["id"]


#: PyJHora's names for the conditional dashas whose applicability it implements.
PYJHORA_CONDITIONAL = {
    "ashtottari": NakshatraDasha.ASHTOTTARI,
    "chaturaaseeti_sama": NakshatraDasha.CHATURASHITI_SAMA,
    "dwadasottari": NakshatraDasha.DWADASHOTTARI,
    "dwisatpathi": NakshatraDasha.DWISAPTATI_SAMA,
    "panchottari": NakshatraDasha.PANCHOTTARI,
    "satabdika": NakshatraDasha.SHATABDIKA,
    "shashtisama": NakshatraDasha.SHASHTIHAYANI,
}


def test_applicability_matches_pyjhora() -> None:
    """Same positions in, same verdicts out (PyJHora has no rule for two systems)."""
    applicable_somewhere = set()
    for case in data()["cases"]:
        sidereal = dict(zip(ORDER, case["grahas"], strict=True))
        verdicts = {
            a.system: a.applicable for a in applicability(case["ascendant"], sidereal, None)
        }
        expected = {PYJHORA_CONDITIONAL[name] for name in case["applicable"]}
        for system in PYJHORA_CONDITIONAL.values():
            assert verdicts[system] == (system in expected), (case["id"], system)
        applicable_somewhere |= expected
    assert len(applicable_somewhere) == len(PYJHORA_CONDITIONAL)
