"""Golden tests: Kalachakra dasha versus PyJHora (PVR book method), same Moon.

The engine and PyJHora agree on the tables, the balance at birth and the
proportional antardashas. They differ in three places, which the comparison
leaves out:

* after the ninth sign of the birth pada, the engine continues with the next pada
  in the zodiac; PyJHora switches to the paired group (savya Ashwini <-> Bharani
  type, apasavya Rohini <-> Mrigashira type), which is the next pada only for
  padas 1-3 and for some pada-4 births;
* PyJHora squeezes the first mahadasha's antardashas into the balance left at
  birth; the engine runs them from the mahadasha's true start, before birth;
* when a sign occurs twice in a pada's sequence, PyJHora starts the antardashas
  from its first occurrence, the engine from the dasha's own place.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest

from jyotish_engine.dasha.kalachakra import (
    NAKSHATRA_GROUP,
    KalachakraGroup,
    birth_position,
    kalachakra_mahadashas,
    kalachakra_sub_periods,
    pada_signs,
)

FIXTURE = Path(__file__).parent / "fixtures" / "sign_dashas_pyjhora.json"
ONE_SECOND = 1.0 / 86400.0
PAIRED = {
    KalachakraGroup.SAVYA_ASHWINI: KalachakraGroup.SAVYA_BHARANI,
    KalachakraGroup.SAVYA_BHARANI: KalachakraGroup.SAVYA_ASHWINI,
    KalachakraGroup.APASAVYA_ROHINI: KalachakraGroup.APASAVYA_MRIGASHIRA,
    KalachakraGroup.APASAVYA_MRIGASHIRA: KalachakraGroup.APASAVYA_ROHINI,
}

pytestmark = pytest.mark.golden


@lru_cache(maxsize=1)
def data() -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return loaded


def _reference_mahadashas(rows: list[Any]) -> list[tuple[int, list[Any]]]:
    """Group PyJHora's antardasha rows by mahadasha: (sign, rows)."""
    groups: list[tuple[int, list[Any]]] = []
    for row in rows:
        if not groups or len(groups[-1][1]) == 9:
            groups.append((row[0][0], []))
        groups[-1][1].append(row)
    return groups


def _same_continuation(birth_pada: int) -> bool:
    if birth_pada % 4 < 3:
        return True
    next_group = NAKSHATRA_GROUP[((birth_pada + 1) % 108) // 4]
    return next_group is PAIRED[NAKSHATRA_GROUP[birth_pada // 4]]


def test_kalachakra_matches_pyjhora() -> None:
    compared_mahas = compared_antars = 0
    for case in data()["cases"]:
        jd = case["jd_ut"]
        ours = kalachakra_mahadashas(case["moon"], jd, case["year_days"])
        theirs = _reference_mahadashas(case["kalachakra"])
        birth_pada, _, _ = birth_position(case["moon"])
        comparable = (
            len(theirs) if _same_continuation(birth_pada) else 9 - birth_position(case["moon"])[1]
        )
        for k, (period, (sign, rows)) in enumerate(zip(ours, theirs[:comparable], strict=False)):
            assert period.sign == sign, (case["id"], k)
            if k + 1 < comparable:
                next_start = jd + theirs[k + 1][1][0][1]
                assert abs(period.end_jd - next_start) < ONE_SECOND, (case["id"], k)
            compared_mahas += 1
            sequence = pada_signs(period.pada)
            if k == 0 or sequence.index(sign) != period.position:
                continue
            for sub, (signs, offset) in zip(kalachakra_sub_periods(period), rows, strict=True):
                assert list(sub.signs) == signs, (case["id"], k, signs)
                assert abs(sub.start_jd - jd - offset) < ONE_SECOND, (case["id"], k, signs)
                compared_antars += 1
    assert compared_mahas > 400
    assert compared_antars > 3000
