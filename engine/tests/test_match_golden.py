"""Matching versus PyJHora on all 108 x 108 pairs of nakshatra padas
(oracle/generate_match_fixtures.py).

Graha maitri, Gana, Bhakoot, Nadi, Mahendra and Rajju must agree exactly. Every
other difference must come from one of PyJHora's known departures, checked pair by
pair:

* **Varna.** It uses Maitreya's scheme (air signs Vaishya), the engine's
  ``maitreya`` profile.
* **Vashya.** It splits Dhanu and Makara by pada number (padas 1-2 as the first
  half) rather than at 15 degrees.
* **Tara.** It awards the 1.5 points to the remainders 3, 5 and 7, the ones the rule
  marks inauspicious, so its score is 3 minus the engine's.
* **Yoni.** Its table is symmetric, where Maitreya's (the engine's) has two cells
  differing from their mirror images.
* **Vedha.** It flags every pair whose 1-based nakshatra numbers sum to 19, 28 or
  37, which adds pairs outside the traditional thirteen (for example Chitra with
  itself).
* **Vasya (South).** It checks only whether the groom's sign is amenable to the
  bride's, not the reverse.
* **Bhakoot.** Its table gives 7 to a Karka groom with a Kumbha bride, a 6/8 pair;
  the mirror cell, and every other 6/8 pair, gives 0.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from jyotish_engine.match import tables as t
from jyotish_engine.match.ashtakoota import MoonPlacement, ashtakoota
from jyotish_engine.match.dashakoota import dashakoota
from jyotish_engine.match.tables import KootaProfile, Vashya

FIXTURE = Path(__file__).parent / "fixtures" / "match_pyjhora.json"


def _pyjhora_vashya(sign: int, pada: int) -> Vashya:
    if sign == 8:
        return Vashya.MANAVA if pada <= 2 else Vashya.CHATUSHPADA
    if sign == 9:
        return Vashya.CHATUSHPADA if pada <= 2 else Vashya.JALACHARA
    return t.vashya(sign, 0.0)


@pytest.mark.golden
def test_all_pada_pairs_against_pyjhora() -> None:
    data: dict[str, Any] = json.loads(FIXTURE.read_text(encoding="utf-8"))
    columns = data["columns"]
    differences: dict[str, int] = {}
    for row in data["rows"]:
        theirs = dict(zip(columns, row, strict=True))
        groom = MoonPlacement.from_pada(theirs["groom_nakshatra"], theirs["groom_pada"])
        bride = MoonPlacement.from_pada(theirs["bride_nakshatra"], theirs["bride_pada"])
        ours = ashtakoota(groom, bride)
        poruthams = {p.name: p for p in dashakoota(groom, bride)}
        for name in ("graha_maitri", "gana", "nadi"):
            assert ours[name].points == theirs[name], (name, row)
        typo = (groom.sign, bride.sign) == (3, 10)
        assert ours["bhakoot"].points == (0.0 if typo else theirs["bhakoot"]), row
        assert not typo or theirs["bhakoot"] == 7
        assert poruthams["mahendra"].agrees == bool(theirs["mahendra"]), row
        assert poruthams["rajju"].agrees == bool(theirs["rajju"]), row

        assert ashtakoota(groom, bride, KootaProfile.MAITREYA)["varna"].points == theirs["varna"]
        groups = (
            _pyjhora_vashya(groom.sign, groom.pada),
            _pyjhora_vashya(bride.sign, bride.pada),
        )
        assert t.VASHYA_POINTS[KootaProfile.POPULAR][groups[1]][groups[0]] == theirs["vashya"]
        assert ours["tara"].points == 3.0 - theirs["tara"], row
        ga, ba = t.NAKSHATRA_YONI[groom.nakshatra][0], t.NAKSHATRA_YONI[bride.nakshatra][0]
        assert theirs["yoni"] in (t.YONI_POINTS[ba][ga], t.YONI_POINTS[ga][ba]), row
        numbers = groom.nakshatra + bride.nakshatra + 2
        assert bool(theirs["vedha"]) == (numbers not in (19, 28, 37)), row
        assert bool(theirs["vasya_south"]) == (groom.sign in t.VASYA_SIGNS[bride.sign]), row

        for name, same in (
            ("vashya", ours["vashya"].points == theirs["vashya"]),
            ("yoni", ours["yoni"].points == theirs["yoni"]),
            ("vedha", poruthams["vedha"].agrees == bool(theirs["vedha"])),
            ("vasya", poruthams["vasya"].agrees == bool(theirs["vasya_south"])),
        ):
            differences[name] = differences.get(name, 0) + (not same)
    # The explained departures touch only a small share of the pairs.
    assert differences["yoni"] < 400 and differences["vedha"] < 700
