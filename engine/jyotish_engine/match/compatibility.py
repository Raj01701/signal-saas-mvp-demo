"""Checks beyond the Moon's kootas that astrologers make before advising a match.

- **Papasamya** (South Indian practice): malefics (the Sun, Mars, Saturn, Rahu and
  Ketu) in the 1st, 2nd, 4th, 7th, 8th or 12th house counted from the lagna, the Moon
  and Venus give papa points, 1 from the lagna, ½ from the Moon and ¼ from Venus. The
  match is balanced when the bride's total does not exceed the groom's.
- **Lagna lords and navamsa lagnas:** the natural relationship of the two lagna lords,
  and the distance between the two navamsa lagnas (2/12 and 6/8 are hard, as in
  Bhakoot).
- **Moon in the other's chart:** each partner's Moon counted from the other's lagna;
  angles and trines are harmonious, the 6th, 8th and 12th strained.
- **Dasha sandhi:** both partners' mahadashas changing within a year of each other is
  read as a time of upheaval for the couple; Rahu to Jupiter for the groom, Venus to the
  Sun for the bride and Mars to Rahu for either are named as hostile junctions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from itertools import pairwise

from jyotish_engine.astro.bodies import Body
from jyotish_engine.core.dignity import Relationship, natural_relationship
from jyotish_engine.core.zodiac import SIGN_LORDS, Sign
from jyotish_engine.models import (
    ChartResult,
    CompatibilityCheckOut,
    DashaSandhiOut,
    PapasamyaItemOut,
    PapasamyaOut,
)
from jyotish_engine.rules.schema import ordinal

MALEFICS = (Body.SUN, Body.MARS, Body.SATURN, Body.RAHU, Body.KETU)
PAPA_HOUSES = (1, 2, 4, 7, 8, 12)
#: Weight of a papa point counted from each reference.
PAPA_WEIGHTS = {"lagna": 1.0, "Moon": 0.5, "Venus": 0.25}
#: Mahadasha changes named as hostile junctions, and for whom.
HOSTILE_SANDHI: dict[tuple[Body, Body], tuple[str, ...]] = {
    (Body.RAHU, Body.JUPITER): ("groom",),
    (Body.VENUS, Body.SUN): ("bride",),
    (Body.MARS, Body.RAHU): ("groom", "bride"),
}
SANDHI_DAYS = 365


def _signs(chart: ChartResult) -> dict[Body, int]:
    return {g.body: int(g.sign) for g in chart.grahas}


def papasamya(chart: ChartResult) -> PapasamyaOut:
    """Papa points of one chart: malefics in the papa houses from the lagna, Moon and Venus."""
    signs = _signs(chart)
    references = {
        "lagna": int(chart.ascendant.sign),
        "Moon": signs[Body.MOON],
        "Venus": signs[Body.VENUS],
    }
    items = []
    for reference, sign in references.items():
        for body in MALEFICS:
            house = (signs[body] - sign) % 12 + 1
            if house in PAPA_HOUSES:
                items.append(
                    PapasamyaItemOut(
                        planet=body,
                        reference=reference,
                        house=house,
                        points=PAPA_WEIGHTS[reference],
                    )
                )
    return PapasamyaOut(points=sum(i.points for i in items), items=items)


def _distance(a: int, b: int) -> int:
    """Counted inclusively from sign ``a`` to sign ``b`` (1-12)."""
    return (b - a) % 12 + 1


def _pair_tone(a: int, b: int) -> str:
    there, back = _distance(a, b), _distance(b, a)
    pair = {there, back}
    if pair == {6, 8}:
        return "hard"
    if pair == {2, 12}:
        return "mixed"
    return "good"


def _relation(a: Body, b: Body) -> str:
    one, other = natural_relationship(a, b), natural_relationship(b, a)
    if a is b:
        return "good"
    if min(one, other) <= Relationship.ENEMY:
        return "hard" if max(one, other) <= Relationship.NEUTRAL else "mixed"
    return "good" if min(one, other) >= Relationship.NEUTRAL else "mixed"


def _word(relation: Relationship) -> str:
    return relation.name.lower().replace("_", " ")


def _moon_tone(house: int) -> str:
    if house in (1, 4, 5, 7, 9, 10):
        return "good"
    return "hard" if house in (6, 8, 12) else "mixed"


def cross_checks(groom: ChartResult, bride: ChartResult) -> list[CompatibilityCheckOut]:
    """The lagna lords, navamsa lagnas and each Moon in the other's chart."""
    g_lagna, b_lagna = int(groom.ascendant.sign), int(bride.ascendant.sign)
    g_lord, b_lord = SIGN_LORDS[Sign(g_lagna)], SIGN_LORDS[Sign(b_lagna)]
    checks = [
        CompatibilityCheckOut(
            key="lagna_lords",
            tone=_relation(g_lord, b_lord),
            detail=(
                f"the lagna lords are {g_lord.value.title()} and {b_lord.value.title()}, "
                f"{_word(natural_relationship(g_lord, b_lord))} one way and "
                f"{_word(natural_relationship(b_lord, g_lord))} the other"
            ),
        )
    ]
    g_d9 = next(v for v in groom.vargas if v.division == 9)
    b_d9 = next(v for v in bride.vargas if v.division == 9)
    a, b = int(g_d9.ascendant.sign), int(b_d9.ascendant.sign)
    checks.append(
        CompatibilityCheckOut(
            key="navamsa_lagnas",
            tone=_pair_tone(a, b),
            detail=(
                f"the navamsa lagnas are {Sign(a).name.title()} and {Sign(b).name.title()}, "
                f"{_distance(a, b)} and {_distance(b, a)} signs apart"
            ),
        )
    )
    for key, person, moon_of, lagna_of in (
        ("groom_moon", "groom", groom, b_lagna),
        ("bride_moon", "bride", bride, g_lagna),
    ):
        moon = _signs(moon_of)[Body.MOON]
        house = _distance(lagna_of, moon)
        checks.append(
            CompatibilityCheckOut(
                key=key,
                tone=_moon_tone(house),
                detail=(
                    f"the {person}'s Moon falls in the {ordinal(house)} house of the other's chart"
                ),
            )
        )
    return checks


def _changes(chart: ChartResult, start: date, end: date) -> list[tuple[date, Body, Body]]:
    """Mahadasha changes between ``start`` and ``end``: (date, from lord, to lord)."""
    mahadashas = [p for p in chart.dashas.vimshottari.periods if len(p.lords) == 1]
    out = []
    for before, after in pairwise(mahadashas):
        when = after.start.date()
        if start <= when < end:
            out.append((when, before.lords[0], after.lords[0]))
    return out


def _change(change: tuple[date, Body, Body]) -> str:
    when, before, after = change
    return f"{before.value.title()} to {after.value.title()}, {when:%B %Y}"


def dasha_sandhi(
    groom: ChartResult, bride: ChartResult, today: date, years: int = 10
) -> DashaSandhiOut:
    """Mahadasha changes of both partners in the coming years, and any within a year of
    each other."""
    end = today.replace(year=today.year + years)
    g, b = _changes(groom, today, end), _changes(bride, today, end)
    close = [(gd, bd) for gd, *_ in g for bd, *_ in b if abs((gd - bd).days) <= SANDHI_DAYS]
    hostile = [
        f"the {who}'s {a.value.title()} to {b_.value.title()} change in {when:%B %Y}"
        for person, changes in (("groom", g), ("bride", b))
        for when, a, b_ in changes
        for who in HOSTILE_SANDHI.get((a, b_), ())
        if who == person
    ]
    return DashaSandhiOut(
        groom_changes=[_change(c) for c in g],
        bride_changes=[_change(c) for c in b],
        within_a_year=bool(close),
        hostile=hostile,
    )


@dataclass(frozen=True, slots=True)
class Balance:
    groom: float
    bride: float

    @property
    def balanced(self) -> bool:
        return self.bride <= self.groom


def papa_balance(groom: ChartResult, bride: ChartResult) -> Balance:
    return Balance(papasamya(groom).points, papasamya(bride).points)
