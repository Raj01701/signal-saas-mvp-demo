"""Jaimini sign rules shared by the sign (rashi) dashas.

Following P.V.R. Narasimha Rao, *Vedic Astrology: An Integrated Approach* (chapters
on Narayana and Chara dasa), which Jagannatha Hora also follows:

* **Footedness.** Aries, Taurus, Gemini, Libra, Scorpio and Sagittarius are
  odd-footed (savya); the other six are even-footed (apasavya). Counts from an
  odd-footed sign run zodiacally, from an even-footed sign backwards.
* **Dasha years of a sign.** Count from the sign to the sign holding its lord
  (both inclusive, in the sign's direction) and subtract one. A lord in the sign
  itself gives 12 years. An exalted lord adds a year, a debilitated one takes a
  year away. Scorpio and Aquarius use their stronger co-lord; when both co-lords
  occupy the sign, the dasha is 12 years.
* **Stronger of two signs**, first rule that decides: (1) more grahas in it;
  (2) more of Jupiter, Mercury and its lord (Mars for Scorpio, Saturn for
  Aquarius) in it or aspecting it by rashi drishti; (3) an exalted graha in it;
  (4) its lord in a sign of the opposite oddity (odd or even sign); (5) natural
  strength, dual over fixed over movable; (6) its lord further advanced in its
  own sign.
"""

from __future__ import annotations

from collections.abc import Mapping

from jyotish_engine.astro.bodies import GRAHAS, Body
from jyotish_engine.core.aspects import rashi_aspected_signs
from jyotish_engine.core.dignity import CO_LORDS, is_debilitated, is_exalted
from jyotish_engine.core.zodiac import SIGN_LORDS, Sign
from jyotish_engine.special.arudha import stronger_co_lord

ODD_FOOTED = frozenset({0, 1, 2, 6, 7, 8})


def sign_index(longitude: float) -> int:
    return int(longitude // 30.0) % 12


def count_signs(start: int, end: int, forward: bool = True) -> int:
    """Signs from ``start`` to ``end`` inclusive, 1 to 12, in the given direction."""
    return ((end - start) % 12 if forward else (start - end) % 12) + 1


def is_odd_sign(sign: int) -> bool:
    """Aries, Gemini, Leo...: the odd signs (index 0, 2, 4... from Aries)."""
    return sign % 2 == 0


def dasha_years(sign: int, sidereal: Mapping[Body, float], lord: Body | None = None) -> int:
    """Dasha length of ``sign`` in years (Chara and Narayana dashas)."""
    positions = dict(sidereal)
    co_lords = CO_LORDS.get(Sign(sign))
    if co_lords and all(sign_index(positions[b]) == sign for b in co_lords):
        return 12
    lord = lord or stronger_co_lord(Sign(sign), positions)
    lord_sign = sign_index(positions[lord])
    count = count_signs(sign, lord_sign, forward=sign in ODD_FOOTED)
    years = count - 1 if count > 1 else 12
    if is_exalted(lord, Sign(lord_sign)):
        years += 1
    elif is_debilitated(lord, Sign(lord_sign)):
        years -= 1
    return years


def dasha_lord(sign: int, sidereal: Mapping[Body, float]) -> Body:
    """Lord of ``sign`` for dasha purposes: a tie between co-lords goes to the one
    that gives the longer dasha."""
    positions = dict(sidereal)
    return stronger_co_lord(
        Sign(sign), positions, tie_break=lambda lord: dasha_years(sign, positions, lord)
    )


def stronger_sign(a: int, b: int, sidereal: Mapping[Body, float]) -> int:
    """The stronger of signs ``a`` and ``b`` (Jaimini rules, see module docstring)."""
    positions = dict(sidereal)
    signs = {body: sign_index(positions[body]) for body in GRAHAS}

    def occupants(x: int) -> int:
        return sum(1 for s in signs.values() if s == x)

    def support(x: int) -> int:
        helpers = {Body.JUPITER, Body.MERCURY, SIGN_LORDS[Sign(x)]}
        return sum(1 for h in helpers if signs[h] == x or x in rashi_aspected_signs(signs[h]))

    def exalted_occupant(x: int) -> bool:
        return any(is_exalted(body, Sign(x)) for body, s in signs.items() if s == x)

    def lord_in_opposite_oddity(x: int) -> bool:
        return is_odd_sign(x) != is_odd_sign(signs[SIGN_LORDS[Sign(x)]])

    for measure in (occupants, support, exalted_occupant, lord_in_opposite_oddity):
        ma, mb = measure(a), measure(b)
        if ma != mb:
            return a if ma > mb else b
    nature_a, nature_b = a % 3, b % 3  # 0 movable, 1 fixed, 2 dual
    if nature_a != nature_b:
        return a if nature_a > nature_b else b
    lord_a = stronger_co_lord(Sign(a), positions)
    lord_b = stronger_co_lord(Sign(b), positions)
    return a if positions[lord_a] % 30.0 > positions[lord_b] % 30.0 else b
