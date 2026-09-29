"""Arudha padas (bhava arudhas A1-A12) and the stronger co-lord of Scorpio and Aquarius.

Arudha of a house: count from the house to its lord, then count the same number
of signs again from the lord. If that lands in the house itself or the 7th from
it, take the 10th sign from that point instead (BPHS; Jaimini Upadesha Sutras).

Scorpio and Aquarius each have two lords (Mars/Ketu, Saturn/Rahu). The stronger
is chosen by the rules in P.V.R. Narasimha Rao, *Vedic Astrology: An Integrated
Approach*, applied in this order:

0. If one lord occupies the sign and the other does not, the one outside rules.
1. The lord conjoined by more planets is stronger (the ascendant is not a planet;
   PyJHora counts it, so charts where the Lagna sits with a co-lord can differ).
2. The lord conjoined or aspected (rashi drishti) by more of Jupiter, Mercury and
   its own dispositor is stronger (a planet never counts as supporting itself).
3. An exalted lord beats one that is not exalted.
4. A lord in a dual sign beats one in a fixed sign, which beats one in a movable
   sign.
5. The lord more advanced in its sign is stronger.
"""

from __future__ import annotations

from jyotish_engine.astro.bodies import GRAHAS, Body
from jyotish_engine.core.aspects import rashi_aspected_signs
from jyotish_engine.core.dignity import CO_LORDS, is_exalted
from jyotish_engine.core.zodiac import SIGN_LORDS, Sign

_NATURE_RANK = {0: 1, 1: 2, 2: 3}  # movable, fixed, dual


def stronger_co_lord(sign: Sign, sidereal: dict[Body, float]) -> Body:
    """Lord of ``sign``, choosing between the two co-lords of Scorpio or Aquarius."""
    if sign not in CO_LORDS:
        return SIGN_LORDS[sign]
    a, b = CO_LORDS[sign]
    sign_of = {body: int(sidereal[body] // 30.0) % 12 for body in GRAHAS}

    a_in, b_in = sign_of[a] == sign, sign_of[b] == sign
    if a_in and not b_in:
        return b
    if b_in and not a_in:
        return a

    def conjoined(body: Body) -> int:
        return sum(1 for other in GRAHAS if other is not body and sign_of[other] == sign_of[body])

    ca, cb = conjoined(a), conjoined(b)
    if ca != cb:
        return a if ca > cb else b

    def supporters(body: Body) -> int:
        house = sign_of[body]
        aspected = set(rashi_aspected_signs(house))
        dispositor = SIGN_LORDS[Sign(house)]
        count = 0
        for helper in (Body.JUPITER, Body.MERCURY, dispositor):
            if helper is body:
                continue
            helper_sign = sign_of[helper]
            if helper_sign == house or helper_sign in aspected:
                count += 1
        return count

    sa, sb = supporters(a), supporters(b)
    if sa != sb:
        return a if sa > sb else b

    ea, eb = is_exalted(a, Sign(sign_of[a])), is_exalted(b, Sign(sign_of[b]))
    if ea != eb:
        return a if ea else b

    na, nb = _NATURE_RANK[sign_of[a] % 3], _NATURE_RANK[sign_of[b] % 3]
    if na != nb:
        return a if na > nb else b

    return a if sidereal[a] % 30.0 > sidereal[b] % 30.0 else b


def arudha_of_sign(house_sign: int, lord_sign: int) -> int:
    distance = (lord_sign - house_sign) % 12
    arudha = (lord_sign + distance) % 12
    if (arudha - house_sign) % 12 in (0, 6):
        arudha = (arudha + 9) % 12
    return arudha


def bhava_arudhas(ascendant_sign: int, sidereal: dict[Body, float]) -> list[int]:
    """Signs of A1 (Arudha Lagna) through A12 (Upapada)."""
    result = []
    for house in range(12):
        sign = Sign((ascendant_sign + house) % 12)
        lord = stronger_co_lord(sign, sidereal)
        result.append(arudha_of_sign(sign, int(sidereal[lord] // 30.0) % 12))
    return result
