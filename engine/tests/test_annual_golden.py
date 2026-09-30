"""Golden tests: annual return moments versus Swiss Ephemeris; Patyayini versus PyJHora.

The reference finds the Varsha Pravesha (solar return) and the Tithi Pravesha
independently, by bisecting Swiss Ephemeris positions (Lahiri, apparent). Times are
compared in TT: for future years the tools predict Delta T differently, by about a
second in the 2030s, which would otherwise show up as a UT difference. The Patyayini
dasha is compared with PyJHora given the same krisamsas and year length.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest

from jyotish_engine.annual.dashas import (
    SEVEN,
    patyayini_dashas,
    patyayini_scheme,
    patyayini_sub_periods,
)
from jyotish_engine.annual.returns import tithi_pravesha, varsha_pravesha
from jyotish_engine.astro.bodies import Body
from jyotish_engine.astro.series import jd_ut_to_tt

FIXTURE = Path(__file__).parent / "fixtures" / "annual_swisseph.json"

pytestmark = pytest.mark.golden


@lru_cache(maxsize=1)
def data() -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return loaded


def _tt_difference_s(ours_ut: float, case: dict[str, Any], key: str) -> float:
    """Difference in TT, so the tools' own Delta T predictions do not count."""
    ours_tt = float(jd_ut_to_tt([ours_ut])[0])
    theirs_tt = case[key] + case[f"{key}_delta_t_days"]
    return abs(ours_tt - theirs_tt) * 86400.0


def test_varsha_pravesha_within_a_second() -> None:
    for case in data()["cases"]:
        ours = varsha_pravesha(case["birth_jd_ut"], case["sun"], case["years_completed"])
        assert _tt_difference_s(ours, case, "varsha_pravesha") < 1.0, case["id"]


def test_tithi_pravesha_within_a_second() -> None:
    for case in data()["cases"]:
        ours = tithi_pravesha(
            case["birth_jd_ut"], case["sun"], case["moon"], case["years_completed"]
        )
        assert _tt_difference_s(ours, case, "tithi_pravesha") < 1.0, case["id"]


def test_patyayini_matches_pyjhora() -> None:
    names = {str(i): body.value for i, body in enumerate(SEVEN)} | {"lagna": "lagna"}
    for case in data()["cases"]:
        krisamsas = case["patyayini_krisamsas"]
        sidereal: dict[Body, float] = {
            Body(names[k]): v for k, v in krisamsas.items() if k != "lagna"
        }
        scheme = patyayini_scheme(krisamsas["lagna"], sidereal)
        start = case["varsha_pravesha"]
        ours = [
            sub
            for maha in patyayini_dashas(scheme, start, case["patyayini_year_days"])
            for sub in patyayini_sub_periods(scheme, maha)
        ]
        rows = case["patyayini"]
        assert len(ours) == len(rows)
        for period, (lords, offset) in zip(ours, rows, strict=True):
            assert list(period.lords) == [names[str(x)] for x in lords], case["id"]
            assert abs(period.start_jd - start - offset) * 86400.0 < 1.0, case["id"]
