"""Gochara: transits read from the natal Moon (or lagna), with vedha, and double transit.

**Favourable houses and vedha** (Phaladeepika, ch. 26). Each graha gives good
results from certain houses counted from the natal Moon, unless another graha
transits the paired *vedha* (obstruction) house at the same time. The Sun and
Saturn do not obstruct each other, nor do the Moon and Mercury.

**Vipareeta vedha.** Some texts apply the pairs in reverse: a graha in one of its
vedha houses (an unfavourable place) has its evil obstructed by a graha in the
paired favourable house. Reported separately as ``relieved_by``.

**Double transit** (popularised by K.N. Rao): a house is activated when Jupiter and
Saturn both influence it at the same time, each by occupying it or by aspecting it
with its graha drishti (Jupiter 5, 7, 9; Saturn 3, 7, 10).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from jyotish_engine.astro.bodies import GRAHAS, Body
from jyotish_engine.core.aspects import graha_aspected_signs
from jyotish_engine.settings import Settings
from jyotish_engine.transit.timeline import house_from, sign_at, sign_timeline

#: Favourable house from the Moon -> its vedha house (Phaladeepika 26).
VEDHA: dict[Body, dict[int, int]] = {
    Body.SUN: {3: 9, 6: 12, 10: 4, 11: 5},
    Body.MOON: {1: 5, 3: 9, 6: 12, 7: 2, 10: 4, 11: 8},
    Body.MARS: {3: 12, 6: 9, 11: 5},
    Body.MERCURY: {2: 5, 4: 3, 6: 9, 8: 1, 10: 8, 11: 12},
    Body.JUPITER: {2: 12, 5: 4, 7: 3, 9: 10, 11: 8},
    Body.VENUS: {1: 8, 2: 7, 3: 1, 4: 10, 5: 9, 8: 5, 9: 11, 11: 6, 12: 3},
    Body.SATURN: {3: 12, 6: 9, 11: 5},
    Body.RAHU: {3: 12, 6: 9, 11: 5},
    Body.KETU: {3: 12, 6: 9, 11: 5},
}

NO_VEDHA: frozenset[frozenset[Body]] = frozenset(
    {frozenset({Body.SUN, Body.SATURN}), frozenset({Body.MOON, Body.MERCURY})}
)


@dataclass(frozen=True, slots=True)
class GocharaPlacement:
    body: Body
    sign: int
    house: int  # 1-based from the reference sign
    favourable: bool
    #: Grahas in the vedha house that obstruct a favourable transit.
    obstructed_by: tuple[Body, ...]
    #: Grahas in the paired favourable house that obstruct an unfavourable one.
    relieved_by: tuple[Body, ...]


def _can_obstruct(a: Body, b: Body) -> bool:
    return a is not b and frozenset({a, b}) not in NO_VEDHA


def gochara(transit_signs: Mapping[Body, int], reference_sign: int) -> list[GocharaPlacement]:
    """Evaluate each graha's transit from ``reference_sign`` (normally the Moon's)."""
    houses = {body: house_from(reference_sign, sign) for body, sign in transit_signs.items()}

    def occupants(house: int, body: Body) -> tuple[Body, ...]:
        return tuple(
            other for other in GRAHAS if houses.get(other) == house and _can_obstruct(body, other)
        )

    out = []
    for body in GRAHAS:
        if body not in transit_signs:
            continue
        house = houses[body]
        pairs = VEDHA[body]
        favourable = house in pairs
        obstructed: tuple[Body, ...] = ()
        relieved: tuple[Body, ...] = ()
        if favourable:
            obstructed = occupants(pairs[house], body)
        else:
            good = next((g for g, v in pairs.items() if v == house), None)
            if good is not None:
                relieved = occupants(good, body)
        out.append(
            GocharaPlacement(body, transit_signs[body], house, favourable, obstructed, relieved)
        )
    return out


def gochara_at(
    jd_ut: float, reference_sign: int, settings: Settings | None = None
) -> list[GocharaPlacement]:
    signs = {body: sign_at(body, jd_ut, settings) for body in GRAHAS}
    return gochara(signs, reference_sign)


@dataclass(frozen=True, slots=True)
class DoubleTransit:
    house: int  # 1-based from the reference sign
    sign: int
    start_jd_ut: float
    end_jd_ut: float


def influenced_signs(body: Body, sign: int) -> set[int]:
    """Signs a graha influences by occupation or graha drishti."""
    return {sign, *graha_aspected_signs(body, sign)}


def double_transits(
    reference_sign: int,
    start_jd_ut: float,
    end_jd_ut: float,
    settings: Settings | None = None,
) -> list[DoubleTransit]:
    """Intervals when Jupiter and Saturn both influence a house, in time order."""
    jupiter = sign_timeline(Body.JUPITER, start_jd_ut, end_jd_ut, settings)
    saturn = sign_timeline(Body.SATURN, start_jd_ut, end_jd_ut, settings)
    open_since: dict[int, float] = {}
    found: list[DoubleTransit] = []
    j = s = 0
    t = start_jd_ut
    while j < len(jupiter) and s < len(saturn):
        end = min(jupiter[j].end_jd_ut, saturn[s].end_jd_ut)
        both = influenced_signs(Body.JUPITER, jupiter[j].sign) & influenced_signs(
            Body.SATURN, saturn[s].sign
        )
        for sign in list(open_since):
            if sign not in both:
                begin = open_since.pop(sign)
                found.append(DoubleTransit(house_from(reference_sign, sign), sign, begin, t))
        for sign in both:
            open_since.setdefault(sign, t)
        t = end
        if jupiter[j].end_jd_ut <= end:
            j += 1
        if saturn[s].end_jd_ut <= end:
            s += 1
    for sign, begin in open_since.items():
        found.append(DoubleTransit(house_from(reference_sign, sign), sign, begin, end_jd_ut))
    return sorted(found, key=lambda d: (d.start_jd_ut, d.house))
