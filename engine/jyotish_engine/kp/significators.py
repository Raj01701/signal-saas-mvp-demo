"""KP (Krishnamurti Paddhati): cusp lords, bhava placement, four-level
significators, ruling planets and horary cusps.

Houses are Placidus bhavas from one cusp to the next, sidereal with the chart's
ayanamsa (the KP preset uses the Krishnamurti ayanamsa). Following the KP Readers,
a planet signifies a house at four levels, strongest first:

1. it is in the star (nakshatra) of an occupant of the house;
2. it occupies the house;
3. it is in the star of the house's owner, the lord of the sign on its cusp;
4. it owns the house.

Rahu and Ketu also act as agents of the lord of the sign they occupy, so they
signify that planet's houses too (occupied at level 2, owned at level 4). Lords of
intercepted signs are not counted as owners.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from jyotish_engine.astro.ayanamsa import true_ayanamsa
from jyotish_engine.astro.bodies import GRAHAS, Body
from jyotish_engine.astro.houses import HouseSystem, chart_angles, quadrant_cusps
from jyotish_engine.astro.time import Instant
from jyotish_engine.core.zodiac import SIGN_LORDS, Sign
from jyotish_engine.kp.subdivisions import KpLords, kp_horary_ascendant, kp_lords
from jyotish_engine.settings import Settings

NODES = (Body.RAHU, Body.KETU)
#: Weekday lords, Sunday first.
DAY_LORDS = (Body.SUN, Body.MOON, Body.MARS, Body.MERCURY, Body.JUPITER, Body.VENUS, Body.SATURN)


def bhava_of(longitude: float, cusps: Sequence[float]) -> int:
    """House (1-12) whose span, from its cusp to the next, contains ``longitude``."""
    for house in range(12):
        start, end = cusps[house], cusps[(house + 1) % 12]
        if (longitude - start) % 360.0 < (end - start) % 360.0:
            return house + 1
    raise ValueError("cusps do not cover the zodiac")


@dataclass(frozen=True, slots=True)
class Significators:
    #: House (1-12) to the planets signifying it at levels 1-4.
    by_house: Mapping[int, tuple[tuple[Body, ...], ...]]
    #: Planet to the houses it signifies at levels 1-4.
    by_planet: Mapping[Body, tuple[tuple[int, ...], ...]]

    def houses_of(self, body: Body) -> tuple[int, ...]:
        """All houses a planet signifies, strongest level first, without repeats."""
        seen: list[int] = []
        for level in self.by_planet[body]:
            seen += [h for h in level if h not in seen]
        return tuple(seen)


def significators(positions: Mapping[Body, float], cusps: Sequence[float]) -> Significators:
    """Four-level significators of the nine grahas for sidereal ``cusps`` (house 1 first)."""
    occupied = {body: bhava_of(lon, cusps) for body, lon in positions.items()}
    star = {body: kp_lords(lon).star_lord for body, lon in positions.items()}
    owners = {house + 1: SIGN_LORDS[Sign(int(cusps[house] % 360.0 // 30.0))] for house in range(12)}
    owned = {body: tuple(h for h, lord in owners.items() if lord is body) for body in GRAHAS}

    def agent_of(body: Body) -> Body | None:
        return SIGN_LORDS[Sign(int(positions[body] % 360.0 // 30.0))] if body in NODES else None

    def levels(body: Body) -> tuple[tuple[int, ...], ...]:
        star_lord, agent = star[body], agent_of(body)
        occupies = (occupied[body],) + ((occupied[agent],) if agent else ())
        owns = owned[body] + (owned[agent] if agent else ())
        return (
            (occupied[star_lord],),
            tuple(dict.fromkeys(occupies)),
            owned[star_lord],
            tuple(dict.fromkeys(owns)),
        )

    by_planet = {body: levels(body) for body in positions}
    by_house = {
        house: tuple(
            tuple(body for body in positions if house in by_planet[body][level])
            for level in range(4)
        )
        for house in range(1, 13)
    }
    return Significators(by_house, by_planet)


@dataclass(frozen=True, slots=True)
class RulingPlanets:
    day_lord: Body
    moon: KpLords
    lagna: KpLords
    #: Rahu or Ketu when it occupies a sign ruled by one of the other ruling planets.
    nodes: tuple[Body, ...]

    @property
    def planets(self) -> tuple[Body, ...]:
        """The ruling planets without repeats: day lord, Moon's then lagna's lords, nodes."""
        chain = (
            self.day_lord,
            self.moon.sign_lord, self.moon.star_lord, self.moon.sub_lord,
            self.lagna.sign_lord, self.lagna.star_lord, self.lagna.sub_lord,
            *self.nodes,
        )  # fmt: skip
        return tuple(dict.fromkeys(chain))


def ruling_planets(
    weekday: int,
    moon_longitude: float,
    lagna_longitude: float,
    node_longitudes: Mapping[Body, float],
) -> RulingPlanets:
    """Ruling planets of a moment; ``weekday`` is 0 for Sunday, counted from sunrise."""
    moon, lagna = kp_lords(moon_longitude), kp_lords(lagna_longitude)
    rulers = {DAY_LORDS[weekday], moon.sign_lord, moon.star_lord, moon.sub_lord}
    rulers |= {lagna.sign_lord, lagna.star_lord, lagna.sub_lord}
    nodes = tuple(
        node
        for node in NODES
        if SIGN_LORDS[Sign(int(node_longitudes[node] % 360.0 // 30.0))] in rulers
    )
    return RulingPlanets(DAY_LORDS[weekday], moon, lagna, nodes)


def _angle_gap(a: float, b: float) -> float:
    return (a - b + 180.0) % 360.0 - 180.0


def horary_cusps(
    number: int, jd_ut: float, latitude: float, longitude: float, settings: Settings | None = None
) -> tuple[float, list[float]]:
    """Moment (UT) nearest ``jd_ut`` at which the sidereal ascendant reaches the start
    of KP division ``number`` (1-249), and the sidereal Placidus cusps then.

    KP horary takes the planets at the time of the question and the cusps from the
    number the querent gives; the cusps are those the place has when that
    ascendant rises.
    """
    settings = settings or Settings()
    target = kp_horary_ascendant(number)

    def sidereal(jd: float, points: Callable[[Instant], Sequence[float]]) -> list[float]:
        instant = Instant.from_jd_ut(jd)
        shift = true_ayanamsa(instant, settings.ayanamsa, settings.user_ayanamsa_j2000)
        return [(p - shift) % 360.0 for p in points(instant)]

    def ascendant_gap(jd: float) -> float:
        asc = sidereal(jd, lambda i: [chart_angles(i, latitude, longitude).ascendant])[0]
        return _angle_gap(asc, target)

    step = 1.0 / 144.0  # ten minutes
    crossings: list[float] = []
    previous = ascendant_gap(jd_ut - 0.55)
    for k in range(1, 159):
        t = jd_ut - 0.55 + k * step
        gap = ascendant_gap(t)
        if previous < 0.0 <= gap and gap - previous < 90.0:
            low, high = t - step, t
            while high - low > 1e-8:
                middle = 0.5 * (low + high)
                if ascendant_gap(middle) < 0.0:
                    low = middle
                else:
                    high = middle
            crossings.append(high)
        previous = gap
    if not crossings:
        raise ValueError("the ascendant does not reach that division here (polar latitude)")
    moment = min(crossings, key=lambda c: abs(c - jd_ut))

    def cusps(instant: Instant) -> list[float]:
        angles = chart_angles(instant, latitude, longitude)
        return list(quadrant_cusps(HouseSystem.PLACIDUS, angles).cusps)

    return moment, sidereal(moment, cusps)
