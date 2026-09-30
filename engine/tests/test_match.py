"""Marriage matching: tables, hand-worked kootas, doshas and their exceptions, the
ten South Indian kutas, and matching two charts."""

from __future__ import annotations

from datetime import datetime

import pytest

from jyotish_engine.chart import compute_chart
from jyotish_engine.match import tables as t
from jyotish_engine.match.ashtakoota import MoonPlacement, ashtakoota
from jyotish_engine.match.compute import compute_match
from jyotish_engine.match.dashakoota import dashakoota
from jyotish_engine.match.tables import KootaProfile
from jyotish_engine.models import BirthInput, PlaceInput
from jyotish_engine.rules.catalogue import Sources, default_knowledge_dir

P = MoonPlacement.from_pada
ASHVINI, BHARANI, ARDRA, PUNARVASU, U_PHALGUNI, CHITRA = 0, 1, 5, 6, 11, 13
ANURADHA, JYESHTHA, MULA = 16, 17, 18


def _points(
    groom: MoonPlacement, bride: MoonPlacement, profile: KootaProfile = KootaProfile.POPULAR
) -> dict[str, float]:
    return {k.name: k.points for k in ashtakoota(groom, bride, profile).kootas}


def test_tables_are_consistent() -> None:
    for animal in range(14):
        assert t.YONI_POINTS[animal][animal] == 4
    for pair in t.YONI_ENEMIES:
        a, b = sorted(pair)
        assert t.YONI_POINTS[a][b] == t.YONI_POINTS[b][a] == 0
    assert all(t.GANA_POINTS[g][g] == 6 for g in range(3))
    for table in t.VASHYA_POINTS.values():
        assert all(table[g][g] == 2.0 for g in range(5))
    for groups in (t.NAKSHATRA_GANA, t.NAKSHATRA_NADI, t.NAKSHATRA_RAJJU):
        assert len(groups) == 27
    assert sorted(len([n for n in range(27) if t.NAKSHATRA_RAJJU[n] is r]) for r in t.Rajju) == [
        3, 6, 6, 6, 6,
    ]  # fmt: skip
    assert len(t.VEDHA_PAIRS) == 13 and sum(len(p) for p in t.VEDHA_PAIRS) == 26
    # Both halves of Dhanu and Makara.
    assert (t.vashya(8, 14.9), t.vashya(8, 15.0)) == (t.Vashya.MANAVA, t.Vashya.CHATUSHPADA)
    assert (t.vashya(9, 14.9), t.vashya(9, 15.0)) == (t.Vashya.CHATUSHPADA, t.Vashya.JALACHARA)


def test_same_birth_star() -> None:
    result = ashtakoota(P(ASHVINI, 1), P(ASHVINI, 1))
    assert _points(P(ASHVINI, 1), P(ASHVINI, 1)) == {
        "varna": 1, "vashya": 2, "tara": 3, "yoni": 4, "graha_maitri": 5, "gana": 6,
        "bhakoot": 7, "nadi": 0,
    }  # fmt: skip
    assert result.total == 28
    nadi = next(d for d in result.doshas if d.name == "nadi")
    assert nadi.present and not nadi.cancelled  # same nakshatra, sign and pada


def test_kootas_by_hand() -> None:
    # Groom Punarvasu 1 (Gemini), bride Ashvini 1 (Aries): the groom's star is the
    # 7th from the bride's (Vadha), hers the 22nd from his (remainder 4, good).
    assert _points(P(PUNARVASU, 1), P(ASHVINI, 1))["tara"] == 1.5
    # Varna differs by profile: a Gemini groom is Shudra (popular) or Vaishya
    # (Maitreya); a Taurus bride is Vaishya or Shudra.
    groom, bride = P(ARDRA, 1), P(3, 1)  # Ardra (Gemini), Rohini (Taurus)
    assert _points(groom, bride)["varna"] == 0
    assert _points(groom, bride, KootaProfile.MAITREYA)["varna"] == 1
    # Moon (Cancer) and Mercury (Gemini): friend one way, enemy the other.
    cancer, gemini = P(7, 2), P(ARDRA, 2)  # Pushya, Ardra
    assert _points(cancer, gemini)["graha_maitri"] == 1.0
    assert _points(cancer, gemini, KootaProfile.MAITREYA)["graha_maitri"] == 2.0
    # Gana: bride's gana picks the row, groom's the column.
    assert _points(P(ASHVINI, 1), P(MULA, 1))["gana"] == 1  # Deva groom, Rakshasa bride
    assert _points(P(MULA, 1), P(ASHVINI, 1))["gana"] == 0  # Rakshasa groom, Deva bride


def test_doshas_and_exceptions() -> None:
    def dosha(groom: MoonPlacement, bride: MoonPlacement, name: str) -> tuple[bool, bool]:
        found = next(d for d in ashtakoota(groom, bride).doshas if d.name == name)
        return found.present, found.cancelled

    # Aries groom, Scorpio bride: 6/8, but Mars rules both signs.
    assert _points(P(ASHVINI, 1), P(ANURADHA, 2))["bhakoot"] == 0
    assert dosha(P(ASHVINI, 1), P(ANURADHA, 2), "bhakoot") == (True, True)
    # Ardra and Punarvasu 1: both Adi nadi, same sign, different nakshatras.
    assert dosha(P(ARDRA, 1), P(PUNARVASU, 1), "nadi") == (True, True)
    # Deva groom, Rakshasa bride whose star is the 19th from his: relieved.
    assert dosha(P(ASHVINI, 1), P(MULA, 1), "gana") == (True, True)
    assert dosha(P(ASHVINI, 1), P(BHARANI, 1), "gana") == (False, False)


def test_ten_kutas() -> None:
    kutas = {p.name: p for p in dashakoota(P(ASHVINI, 1), P(JYESHTHA, 1))}
    assert not kutas["vedha"].agrees  # Ashvini and Jyeshtha obstruct each other
    assert len(kutas) == 10
    cow_tiger = {p.name: p for p in dashakoota(P(U_PHALGUNI, 2), P(CHITRA, 1))}
    assert not cow_tiger["yoni"].agrees and "hostile" in cow_tiger["yoni"].detail
    # Rasi: the groom's sign 7th from the bride's agrees; 2nd from hers does not,
    # unless the lords are the same or friends.
    assert {p.name: p for p in dashakoota(P(14, 1), P(ASHVINI, 1))}["rasi"].agrees  # Libra, Aries
    second = {p.name: p for p in dashakoota(P(3, 1), P(ASHVINI, 1))}["rasi"]  # Taurus, Aries
    assert not second.agrees and second.relieved_by is None  # Venus and Mars are neutral
    # Rajju relief needs Rasyadhipati, Rasi, Dina and Mahendra all to agree.
    relieved = [
        (g, b)
        for g in range(108)
        for b in range(108)
        if {p.name: p for p in dashakoota(P(g // 4, g % 4 + 1), P(b // 4, b % 4 + 1))}[
            "rajju"
        ].relieved_by
    ]
    assert relieved
    g, b = relieved[0]
    kutas = {p.name: p for p in dashakoota(P(g // 4, g % 4 + 1), P(b // 4, b % 4 + 1))}
    assert all(kutas[name].agrees for name in ("rasyadhipati", "rasi", "dina", "mahendra"))


def test_citations_are_known_sources() -> None:
    sources = Sources.load(default_knowledge_dir() / "sources.yaml")
    for by_profile in t.SOURCES.values():
        for citations in by_profile.values():
            for citation in citations:
                sources.check(citation, "match")
    sources.check(t.RAMAN, "match")


@pytest.mark.parametrize("profile", list(KootaProfile))
def test_compute_match_of_two_charts(profile: KootaProfile) -> None:
    delhi = PlaceInput(name="New Delhi", latitude=28.6139, longitude=77.2090)
    groom = compute_chart(BirthInput(local_datetime=datetime(1990, 5, 17, 12, 0), place=delhi))
    bride = compute_chart(BirthInput(local_datetime=datetime(1993, 11, 2, 6, 30), place=delhi))
    result = compute_match(groom, bride, profile)
    assert [k.name for k in result.ashtakoota] == [
        "varna", "vashya", "tara", "yoni", "graha_maitri", "gana", "bhakoot", "nadi",
    ]  # fmt: skip
    assert result.ashtakoota_total == sum(k.points for k in result.ashtakoota) <= 36
    assert all(k.sources for k in result.ashtakoota)
    assert len(result.dashakoota) == 10
    assert result.kuja_balanced == (result.groom_kuja.manglik == result.bride_kuja.manglik)
    assert result.profile == profile.value
