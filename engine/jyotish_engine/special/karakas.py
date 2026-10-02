"""Chara (variable) karakas of Jaimini astrology.

Planets are ranked by the degrees they have travelled within their sign; the most
advanced is the Atmakaraka. In the eight-karaka scheme Rahu is included and its
degrees are counted backwards (30 minus its degrees in sign), because it moves
retrograde.
"""

from __future__ import annotations

from enum import StrEnum

from jyotish_engine.astro.bodies import Body


class Karaka(StrEnum):
    ATMA = "atmakaraka"
    AMATYA = "amatyakaraka"
    BHRATRI = "bhratrikaraka"
    MATRI = "matrikaraka"
    PITRI = "pitrikaraka"
    PUTRA = "putrakaraka"
    GNATI = "gnatikaraka"
    DARA = "darakaraka"


EIGHT_KARAKAS = (
    Karaka.ATMA,
    Karaka.AMATYA,
    Karaka.BHRATRI,
    Karaka.MATRI,
    Karaka.PITRI,
    Karaka.PUTRA,
    Karaka.GNATI,
    Karaka.DARA,
)
SEVEN_KARAKAS = (
    Karaka.ATMA,
    Karaka.AMATYA,
    Karaka.BHRATRI,
    Karaka.MATRI,
    Karaka.PUTRA,
    Karaka.GNATI,
    Karaka.DARA,
)
_SEVEN_PLANETS = (
    Body.SUN,
    Body.MOON,
    Body.MARS,
    Body.MERCURY,
    Body.JUPITER,
    Body.VENUS,
    Body.SATURN,
)


def chara_karakas(sidereal: dict[Body, float], include_rahu: bool = True) -> dict[Karaka, Body]:
    """Map each karaka to its planet. ``sidereal`` holds sidereal longitudes."""
    bodies = [*_SEVEN_PLANETS, Body.RAHU] if include_rahu else list(_SEVEN_PLANETS)

    def advancement(body: Body) -> float:
        degrees = sidereal[body] % 30.0
        return 30.0 - degrees if body is Body.RAHU else degrees

    ranked = sorted(bodies, key=advancement, reverse=True)
    names = EIGHT_KARAKAS if include_rahu else SEVEN_KARAKAS
    return dict(zip(names, ranked, strict=True))
