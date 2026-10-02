"""Aspects (drishti).

* **Graha drishti** (Parashari, sign-based): every graha aspects the 7th sign from
  itself; Mars also the 4th and 8th, Jupiter the 5th and 9th, Saturn the 3rd and
  10th. Rahu and Ketu use the 7th only by default (some schools add the 5th and
  9th; see ``NODE_ASPECTS_5_9``).
* **Rashi drishti** (Jaimini): movable signs aspect the fixed signs except the one
  next to them; fixed signs aspect the movable signs except the one before them;
  dual signs aspect the other dual signs. Planets aspect what their sign aspects.
"""

from __future__ import annotations

from jyotish_engine.astro.bodies import Body

GRAHA_ASPECTS: dict[Body, tuple[int, ...]] = {
    Body.SUN: (7,),
    Body.MOON: (7,),
    Body.MARS: (4, 7, 8),
    Body.MERCURY: (7,),
    Body.JUPITER: (5, 7, 9),
    Body.VENUS: (7,),
    Body.SATURN: (3, 7, 10),
    Body.RAHU: (7,),
    Body.KETU: (7,),
}
NODE_ASPECTS_5_9: tuple[int, ...] = (5, 7, 9)


def graha_aspected_signs(body: Body, sign: int, node_aspects_5_9: bool = False) -> list[int]:
    """Signs aspected by a graha placed in ``sign`` (counting its own sign as 1)."""
    houses = GRAHA_ASPECTS[body]
    if node_aspects_5_9 and body in (Body.RAHU, Body.KETU):
        houses = NODE_ASPECTS_5_9
    return [(sign + h - 1) % 12 for h in houses]


def rashi_aspected_signs(sign: int) -> list[int]:
    """Signs aspected by ``sign`` under Jaimini rashi drishti."""
    modality = sign % 3
    if modality == 0:  # movable: fixed signs except the next sign
        return [s for s in range(12) if s % 3 == 1 and s != (sign + 1) % 12]
    if modality == 1:  # fixed: movable signs except the previous sign
        return [s for s in range(12) if s % 3 == 0 and s != (sign - 1) % 12]
    return [s for s in range(12) if s % 3 == 2 and s != sign]  # dual: other duals


def rashi_aspects(sign_a: int, sign_b: int) -> bool:
    return sign_b in rashi_aspected_signs(sign_a)
