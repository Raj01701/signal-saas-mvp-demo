"""Natural benefics and malefics of a chart (P.V.R. Narasimha Rao's reading of BPHS).

Jupiter and Venus are benefics, and so is the Moon while waxing (Shukla paksha).
The Sun, Mars, Saturn, Rahu, Ketu and the waning Moon are malefics. Mercury is a
benefic when alone in its sign or with at least as many benefics as malefics
there, otherwise a malefic.
"""

from __future__ import annotations

from collections.abc import Mapping

from jyotish_engine.astro.bodies import Body


def waxing_moon(sidereal: Mapping[Body, float]) -> bool:
    return (sidereal[Body.MOON] - sidereal[Body.SUN]) % 360.0 < 180.0


def natural_benefics(sidereal: Mapping[Body, float]) -> set[Body]:
    """The benefics among the grahas present in ``sidereal``."""
    signs = {b: int(lon // 30.0) % 12 for b, lon in sidereal.items()}
    waxing = waxing_moon(sidereal)
    good = {Body.JUPITER, Body.VENUS} | ({Body.MOON} if waxing else set())
    bad = {Body.SUN, Body.MARS, Body.SATURN, Body.RAHU, Body.KETU}
    if not waxing:
        bad.add(Body.MOON)
    company = [b for b, s in signs.items() if s == signs[Body.MERCURY] and b is not Body.MERCURY]
    if sum(b in good for b in company) >= sum(b in bad for b in company):
        good.add(Body.MERCURY)
    return {b for b in good if b in sidereal}


def natural_malefics(sidereal: Mapping[Body, float]) -> set[Body]:
    return set(sidereal) - natural_benefics(sidereal)
