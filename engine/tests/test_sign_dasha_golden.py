"""Golden tests: Jaimini sign dashas versus PyJHora, given identical positions.

Chara dasha (K.N. Rao method) is compared at the mahadasha level: PyJHora gives
every mahadasha the same antardasha order, starting from the lagna, instead of
K.N. Rao's order from the sign after the dasha sign. Narayana dasha is compared
in full: both rounds, mahadashas and antardashas.

PyJHora departs from the rules the engine follows in four ways, each detected
precisely for a chart (see ``_known_differences``):

* it does not treat Mercury in Virgo as exalted (BPHS: exalted);
* it counts the lagna as a planet when choosing between co-lords;
* in the stronger-sign test (rule 2) it counts Jupiter or Mercury twice when it
  also rules the sign, and misses a lord that occupies its own sign;
* when the co-lord rules tie, it prefers the co-lord whose *own* sign has the
  longer dasha, where the engine prefers the co-lord that gives the sign in
  question the longer dasha.

Charts free of all four must match exactly; every chart that does not match must
show at least one of them.
"""

from __future__ import annotations

import json
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest

from jyotish_engine.astro.bodies import GRAHAS, Body
from jyotish_engine.core.aspects import rashi_aspected_signs
from jyotish_engine.core.dignity import CO_LORDS
from jyotish_engine.core.jaimini import dasha_lord, sign_index
from jyotish_engine.core.zodiac import SIGN_LORDS, Sign
from jyotish_engine.dasha.sign import SignDasha, SignPeriod, sign_mahadashas, sign_sub_periods
from jyotish_engine.special.arudha import stronger_co_lord

FIXTURE = Path(__file__).parent / "fixtures" / "sign_dashas_pyjhora.json"
ONE_SECOND = 1.0 / 86400.0

pytestmark = pytest.mark.golden


@lru_cache(maxsize=1)
def data() -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return loaded


def _positions(case: dict[str, Any]) -> dict[Body, float]:
    return dict(zip(GRAHAS, case["grahas"], strict=True))


def _rule2(sign: int, signs: dict[Body, int], pyjhora: bool) -> int:
    lord = SIGN_LORDS[Sign(sign)]
    helpers = (
        [Body.MERCURY, Body.JUPITER, lord] if pyjhora else list({Body.MERCURY, Body.JUPITER, lord})
    )
    conjoined = sum(1 for h in helpers if signs[h] == sign and not (pyjhora and h is lord))
    aspecting = sum(1 for h in helpers if sign in rashi_aspected_signs(signs[h]))
    return conjoined + aspecting


def _rule2_differs(a: int, b: int, signs: dict[Body, int]) -> bool:
    if sum(s == a for s in signs.values()) != sum(s == b for s in signs.values()):
        return False  # decided by rule 1 in both
    ours = _rule2(a, signs, False) - _rule2(b, signs, False)
    theirs = _rule2(a, signs, True) - _rule2(b, signs, True)
    return (ours > 0) - (ours < 0) != (theirs > 0) - (theirs < 0)


def _known_differences(case: dict[str, Any]) -> set[str]:
    sidereal = _positions(case)
    signs = {body: sign_index(lon) for body, lon in sidereal.items()}
    lagna = sign_index(case["ascendant"])
    found = set()
    if signs[Body.MERCURY] == Sign.VIRGO:
        found.add("mercury_in_virgo")
    if any(signs[b] == lagna for pair in CO_LORDS.values() for b in pair):
        found.add("lagna_with_co_lord")
    for sign, (a, _) in CO_LORDS.items():
        first = stronger_co_lord(sign, sidereal, tie_break=lambda b, a=a: float(b is a))
        second = stronger_co_lord(sign, sidereal, tie_break=lambda b, a=a: float(b is not a))
        if first is not second:
            found.add("co_lord_tie")
    comparisons = [(lagna, (lagna + 6) % 12)] + [
        (signs[dasha_lord(s, sidereal)], signs[dasha_lord((s + 6) % 12, sidereal)])
        for s in range(12)
    ]
    if any(_rule2_differs(a, b, signs) for a, b in comparisons):
        found.add("stronger_sign_rule2")
    return found


def _matches(case: dict[str, Any], ours: list[SignPeriod], rows: list[Any]) -> bool:
    for period, (signs, offset) in zip(ours, rows, strict=False):
        if list(period.signs) != signs:
            return False
        if abs(period.start_jd - case["jd_ut"] - offset) > ONE_SECOND:
            return False
    return True


def _chara(case: dict[str, Any]) -> list[SignPeriod]:
    return sign_mahadashas(
        SignDasha.CHARA, case["ascendant"], _positions(case), case["jd_ut"], case["year_days"]
    )


def _narayana(case: dict[str, Any]) -> list[SignPeriod]:
    sidereal = _positions(case)
    mahas = sign_mahadashas(
        SignDasha.NARAYANA, case["ascendant"], sidereal, case["jd_ut"], case["year_days"]
    )
    return [sub for m in mahas for sub in sign_sub_periods(SignDasha.NARAYANA, m, sidereal)]


@pytest.mark.parametrize(("name", "build"), [("chara_kn_rao", _chara), ("narayana", _narayana)])
def test_sign_dashas_match_except_known_differences(name: str, build: Any) -> None:
    exact = 0
    reasons: Counter[str] = Counter()
    unexplained = []
    for case in data()["cases"]:
        known = _known_differences(case)
        if _matches(case, build(case), case[name]):
            exact += 1
        elif known:
            reasons.update(known)
        else:
            unexplained.append(case["id"])
    assert not unexplained, f"mismatches with no known cause: {unexplained}"
    assert exact >= 45, (exact, reasons)
