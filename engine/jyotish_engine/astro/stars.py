"""Fixed stars that anchor the "true" (star-based) ayanamsas.

Catalogue values are from the ESA Hipparcos Catalogue (1997; CDS I/239): ICRS
position at epoch J1991.25, proper motion (mu_alpha* includes cos delta) and
parallax. Radial velocity is ignored; its effect is far below an arcsecond over the
supported date range.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from functools import cache
from typing import Any

from skyfield.api import Star
from skyfield.framelib import ecliptic_frame

from jyotish_engine.astro.ephemeris import get_ephemeris
from jyotish_engine.astro.time import Instant, timescale


@dataclass(frozen=True, slots=True)
class HipparcosStar:
    hip: int
    name: str
    ra_deg: float
    dec_deg: float
    pm_ra_mas: float
    pm_dec_mas: float
    parallax_mas: float


class AnchorStar(StrEnum):
    SPICA = "spica"  # Chitra, alpha Virginis
    REVATI = "revati"  # zeta Piscium
    PUSHYA = "pushya"  # delta Cancri (Asellus Australis)


CATALOGUE: dict[AnchorStar, HipparcosStar] = {
    AnchorStar.SPICA: HipparcosStar(
        65474, "Spica (alpha Vir)", 201.29835230, -11.16124491, -42.50, -31.73, 12.44
    ),
    AnchorStar.REVATI: HipparcosStar(
        5737, "zeta Psc", 18.43250986, 7.57548895, 141.66, -55.62, 22.09
    ),
    AnchorStar.PUSHYA: HipparcosStar(
        42911, "delta Cnc", 131.17129209, 18.15486399, -17.10, -228.46, 23.97
    ),
}


@cache
def skyfield_star(anchor: AnchorStar) -> Any:
    data = CATALOGUE[anchor]
    return Star(
        ra_hours=data.ra_deg / 15.0,
        dec_degrees=data.dec_deg,
        ra_mas_per_year=data.pm_ra_mas,
        dec_mas_per_year=data.pm_dec_mas,
        parallax_mas=data.parallax_mas,
        epoch=timescale().J(1991.25),
    )


def star_longitude(anchor: AnchorStar, instant: Instant, *, apparent: bool) -> float:
    """Tropical ecliptic longitude of a star, true equinox of date (degrees).

    With ``apparent=False`` the position is astrometric: proper motion, parallax and
    light-time are applied, but annual aberration and light deflection are not.
    """
    eph = get_ephemeris()
    position = eph.earth.at(instant.skyfield()).observe(skyfield_star(anchor))
    if apparent:
        position = position.apparent()
    _, lon, _ = position.frame_latlon(ecliptic_frame)
    return float(lon.degrees) % 360.0
