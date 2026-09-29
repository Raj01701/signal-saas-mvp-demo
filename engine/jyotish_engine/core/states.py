"""Planetary conditions: combustion, planetary war, and the Baladi and Jagradadi avasthas."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from itertools import combinations

from jyotish_engine.astro.bodies import Body
from jyotish_engine.astro.positions import angular_distance
from jyotish_engine.core.dignity import Dignity

#: Combustion orbs from the Sun in degrees (Surya Siddhanta), with the smaller orb
#: that applies when Mercury or Venus is retrograde.
COMBUSTION_ORBS: dict[Body, tuple[float, float]] = {
    Body.MOON: (12.0, 12.0),
    Body.MARS: (17.0, 17.0),
    Body.MERCURY: (14.0, 12.0),
    Body.JUPITER: (11.0, 11.0),
    Body.VENUS: (10.0, 8.0),
    Body.SATURN: (15.0, 15.0),
}

#: The five "star planets" that can fight a planetary war.
TARA_GRAHAS = (Body.MARS, Body.MERCURY, Body.JUPITER, Body.VENUS, Body.SATURN)


def is_combust(body: Body, longitude: float, sun_longitude: float, retrograde: bool) -> bool:
    if body not in COMBUSTION_ORBS:
        return False
    direct_orb, retro_orb = COMBUSTION_ORBS[body]
    return angular_distance(longitude, sun_longitude) <= (retro_orb if retrograde else direct_orb)


@dataclass(frozen=True, slots=True)
class PlanetaryWar:
    planets: tuple[Body, Body]
    separation_deg: float
    #: The planet further north in ecliptic latitude (Surya Siddhanta); schools differ.
    winner: Body


def planetary_wars(
    longitudes: dict[Body, float], latitudes: dict[Body, float]
) -> list[PlanetaryWar]:
    """Pairs of tara grahas within one degree of longitude."""
    wars = []
    for a, b in combinations(TARA_GRAHAS, 2):
        separation = angular_distance(longitudes[a], longitudes[b])
        if separation < 1.0:
            winner = a if latitudes[a] >= latitudes[b] else b
            wars.append(PlanetaryWar((a, b), separation, winner))
    return wars


class BaladiAvastha(StrEnum):
    BALA = "bala"  # infant
    KUMARA = "kumara"  # youth
    YUVA = "yuva"  # adult: full results
    VRIDDHA = "vriddha"  # old
    MRITA = "mrita"  # dead: negligible results


def baladi_avastha(sidereal_longitude: float) -> BaladiAvastha:
    """Age state by 6-degree fifths of the sign, reversed in even signs (BPHS)."""
    sign = int(sidereal_longitude // 30.0) % 12
    part = min(int((sidereal_longitude % 30.0) / 6.0), 4)
    if sign % 2 == 1:  # even signs run backwards
        part = 4 - part
    return list(BaladiAvastha)[part]


class JagradadiAvastha(StrEnum):
    JAGRAT = "jagrat"  # awake: exalted or own sign
    SWAPNA = "swapna"  # dreaming: friend's or neutral sign
    SUSHUPTI = "sushupti"  # deep sleep: enemy's sign or debilitated


def jagradadi_avastha(dignity: Dignity) -> JagradadiAvastha:
    if dignity in (Dignity.EXALTED, Dignity.MOOLATRIKONA, Dignity.OWN):
        return JagradadiAvastha.JAGRAT
    if dignity in (Dignity.GREAT_FRIEND, Dignity.FRIEND, Dignity.NEUTRAL):
        return JagradadiAvastha.SWAPNA
    return JagradadiAvastha.SUSHUPTI


def is_gandanta(sidereal_longitude: float) -> bool:
    """Within the last pada of a water sign or the first pada of the next fire sign."""
    longitude = sidereal_longitude % 360.0
    pada = 360.0 / 108.0
    return any(angular_distance(longitude, boundary) < pada for boundary in (0.0, 120.0, 240.0))
