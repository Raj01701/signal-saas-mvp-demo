"""Chart facts: the view of a chart that rules are evaluated against.

Facts can come from a computed chart or from a compact spec, which is how every
rule's test charts are written, for example::

    {"lagna": "aries", "mars": "capricorn 12", "rest": "leo", "retrograde": ["saturn"]}

A position is a sign name, optionally followed by degrees within the sign (15 by
default), or an absolute sidereal longitude. Every graha must be placed, either by
name or through ``rest``. Rahu and Ketu are always opposite: give one of them (the
other follows), or neither, in which case Rahu goes to ``rest`` and Ketu opposite.
Optional keys ``day_birth`` (true or false) and ``gender`` ("male" or "female")
supply the birth facts a few rules need.

Dasha and transit rules also need a period: ``dasha`` lists the running lords,
mahadasha first (``{"dasha": ["jupiter", "venus"]}``), and ``transit`` places the
transiting grahas (``{"transit": {"saturn": "pisces 10"}}``); a transiting graha
that is not given obstructs nothing.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from functools import cached_property
from typing import Any

from jyotish_engine.astro.bodies import GRAHAS, Body
from jyotish_engine.core.aspects import graha_aspected_signs
from jyotish_engine.core.dignity import DIGNITY_RULES, compound_relationship, in_moolatrikona
from jyotish_engine.core.nakshatra import nakshatra_of
from jyotish_engine.core.nature import natural_benefics, waxing_moon
from jyotish_engine.core.states import is_combust, is_gandanta
from jyotish_engine.core.varga import varga_sign
from jyotish_engine.core.zodiac import SIGN_LORDS, Sign
from jyotish_engine.models import ChartResult

SEVEN = (Body.SUN, Body.MOON, Body.MARS, Body.MERCURY, Body.JUPITER, Body.VENUS, Body.SATURN)
NODES = (Body.RAHU, Body.KETU)
SIGN_NAMES = {s.name.lower(): int(s) for s in Sign}
LAGNA = "lagna"
GENDERS = ("male", "female")
KENDRA, TRIKONA, DUSTHANA, UPACHAYA = (1, 4, 7, 10), (1, 5, 9), (6, 8, 12), (3, 6, 10, 11)

#: The seven movable karanas, repeating from the second half of Shukla Pratipada.
MOVABLE_KARANAS = ("bava", "balava", "kaulava", "taitila", "garaja", "vanija", "vishti")
FIXED_KARANAS = {0: "kimstughna", 57: "shakuni", 58: "chatushpada", 59: "naga"}

Point = Body | str  # a graha, or "lagna"


class MissingFactError(LookupError):
    """A rule needs a birth fact (day or night birth, gender) that was not supplied."""


def parse_position(value: Any) -> float:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value) % 360.0
    parts = str(value).split()
    if not parts or parts[0].lower() not in SIGN_NAMES or len(parts) > 2:
        raise ValueError(f"bad position {value!r}: use a sign name, optional degrees")
    degrees = float(parts[1]) if len(parts) > 1 else 15.0
    if not 0.0 <= degrees < 30.0:
        raise ValueError(f"bad position {value!r}: degrees must be in [0, 30)")
    return SIGN_NAMES[parts[0].lower()] * 30.0 + degrees


def _spec_positions(spec: Mapping[str, Any]) -> dict[Body, float]:
    rest = spec.get("rest")
    positions: dict[Body, float] = {}
    for body in SEVEN:
        if body.value in spec:
            positions[body] = parse_position(spec[body.value])
        elif rest is not None:
            positions[body] = parse_position(rest)
        else:
            raise ValueError(f"chart spec places no {body.value} (give it or 'rest')")
    rahu, ketu = spec.get("rahu"), spec.get("ketu")
    if rahu is not None and ketu is not None:
        positions[Body.RAHU], positions[Body.KETU] = parse_position(rahu), parse_position(ketu)
        gap = abs((positions[Body.KETU] - positions[Body.RAHU]) % 360.0 - 180.0)
        if gap > 1e-6:
            raise ValueError("chart spec places Rahu and Ketu not opposite each other")
    elif ketu is not None:
        positions[Body.KETU] = parse_position(ketu)
        positions[Body.RAHU] = (positions[Body.KETU] + 180.0) % 360.0
    else:
        source = rahu if rahu is not None else rest
        if source is None:
            raise ValueError("chart spec places no rahu (give rahu, ketu or 'rest')")
        positions[Body.RAHU] = parse_position(source)
        positions[Body.KETU] = (positions[Body.RAHU] + 180.0) % 360.0
    return positions


@dataclass(frozen=True)
class ChartFacts:
    """Sidereal positions plus the few states and birth facts rules need."""

    lagna: float
    positions: Mapping[Body, float]
    retrograde: frozenset[Body] = field(default_factory=frozenset)
    node_aspects_5_9: bool = False
    day_birth: bool | None = None
    gender: str | None = None
    #: The running dasha lords, mahadasha first (for dasha rules).
    dasha: tuple[Body, ...] = ()
    #: Sidereal longitudes of the transiting grahas (for transit rules).
    transits: Mapping[Body, float] | None = None
    #: Outcomes of the rules evaluated so far, filled by the rule runner so that
    #: rules can refer to each other with ``fires(...)``.
    results: dict[str, bool] = field(default_factory=dict, compare=False, repr=False)

    def __post_init__(self) -> None:
        if self.gender is not None and self.gender not in GENDERS:
            raise ValueError(f"gender must be one of {GENDERS}, got {self.gender!r}")

    @classmethod
    def from_chart(cls, chart: ChartResult, gender: str | None = None) -> ChartFacts:
        return cls(
            lagna=chart.ascendant.sidereal_longitude,
            positions={g.body: g.sidereal_longitude for g in chart.grahas if g.body in GRAHAS},
            retrograde=frozenset(g.body for g in chart.grahas if g.retrograde),
            node_aspects_5_9=chart.settings.node_aspects_5_9,
            day_birth=chart.day.born_during_day,
            gender=gender,
        )

    @classmethod
    def from_spec(cls, spec: Mapping[str, Any]) -> ChartFacts:
        known = {LAGNA, "rest", "retrograde", "day_birth", "gender", "dasha", "transit"}
        known |= {b.value for b in GRAHAS}
        unknown = set(spec) - known
        if unknown:
            raise ValueError(f"unknown keys in chart spec: {sorted(unknown)}")
        if LAGNA not in spec:
            raise ValueError("chart spec has no lagna")
        day_birth = spec.get("day_birth")
        if day_birth is not None and not isinstance(day_birth, bool):
            raise ValueError("day_birth must be true or false")
        return cls(
            lagna=parse_position(spec[LAGNA]),
            positions=_spec_positions(spec),
            retrograde=frozenset(Body(b) for b in spec.get("retrograde", [])),
            day_birth=day_birth,
            gender=spec.get("gender"),
            dasha=tuple(Body(b) for b in spec.get("dasha", [])),
            transits=(
                {Body(b): parse_position(v) for b, v in spec["transit"].items()}
                if "transit" in spec
                else None
            ),
        )

    def with_period(
        self, dasha: tuple[Body, ...] = (), transits: Mapping[Body, float] | None = None
    ) -> ChartFacts:
        """The same chart with a running dasha and transit positions."""
        return replace(self, dasha=dasha, transits=transits, results={})

    # --- signs and houses ---------------------------------------------------

    @cached_property
    def signs(self) -> dict[Body, int]:
        return {b: int(lon // 30.0) % 12 for b, lon in self.positions.items()}

    @cached_property
    def lagna_sign(self) -> int:
        return int(self.lagna // 30.0) % 12

    def sign_of(self, point: Point) -> int:
        return self.lagna_sign if point == LAGNA else self.signs[Body(point)]

    def longitude(self, point: Point) -> float:
        return self.lagna if point == LAGNA else self.positions[Body(point)]

    def house(self, point: Point, reference: Point = LAGNA) -> int:
        """House (1-12, whole-sign) of ``point`` counted from ``reference``."""
        return (self.sign_of(point) - self.sign_of(reference)) % 12 + 1

    def sign_of_house(self, house: int, reference: Point = LAGNA) -> int:
        return (self.sign_of(reference) + house - 1) % 12

    def lord(self, house: int, reference: Point = LAGNA) -> Body:
        return SIGN_LORDS[Sign(self.sign_of_house(house, reference))]

    def dispositor(self, point: Point) -> Body:
        return SIGN_LORDS[Sign(self.sign_of(point))]

    def occupants(self, house: int, reference: Point = LAGNA) -> list[Body]:
        sign = self.sign_of_house(house, reference)
        return [b for b in GRAHAS if self.signs[b] == sign]

    # --- dignity and states --------------------------------------------------

    def exalted(self, body: Body) -> bool:
        return Sign(self.signs[body]) in DIGNITY_RULES[body].exaltation_signs

    def debilitated(self, body: Body) -> bool:
        opposite = Sign((self.signs[body] + 6) % 12)
        return opposite in DIGNITY_RULES[body].exaltation_signs

    def own_sign(self, body: Body) -> bool:
        return Sign(self.signs[body]) in DIGNITY_RULES[body].own_signs

    def moolatrikona(self, body: Body) -> bool:
        lon = self.positions[body]
        return in_moolatrikona(body, Sign(self.signs[body]), lon % 30.0)

    def dignified(self, body: Body) -> bool:
        """Exalted, in moolatrikona or in its own sign."""
        return self.exalted(body) or self.own_sign(body) or self.moolatrikona(body)

    def relation_to_dispositor(self, body: Body) -> str:
        """ "own", or the compound relationship of ``body`` to its sign lord."""
        lord = SIGN_LORDS[Sign(self.signs[body])]
        if lord is body:
            return "own"
        return compound_relationship(body, lord, self.signs[body], self.signs[lord]).name.lower()

    def friendly_sign(self, body: Body) -> bool:
        return self.relation_to_dispositor(body) in ("own", "friend", "great_friend")

    def enemy_sign(self, body: Body) -> bool:
        return self.relation_to_dispositor(body) in ("enemy", "great_enemy")

    def combust(self, body: Body) -> bool:
        return is_combust(
            body, self.positions[body], self.positions[Body.SUN], body in self.retrograde
        )

    def strong(self, body: Body) -> bool:
        """The engine's working test for a "strong" planet in yoga definitions.

        Not debilitated and not combust, and either dignified (exalted,
        moolatrikona, own sign) or placed in a kendra or trikona from the lagna
        outside an enemy's sign. Classical texts leave "strong" undefined; a reviewer
        may later replace this with a Shadbala threshold.
        """
        if self.debilitated(body) or self.combust(body):
            return False
        if self.dignified(body):
            return True
        return not self.enemy_sign(body) and self.house(body) in (*KENDRA, *TRIKONA)

    def exaltation_lord(self, body: Body) -> Body:
        return SIGN_LORDS[DIGNITY_RULES[body].exaltation_signs[0]]

    def navamsa_sign(self, point: Point) -> int:
        return int(varga_sign(self.longitude(point), 9))

    # --- nature and aspects -----------------------------------------------------

    @cached_property
    def benefics(self) -> set[Body]:
        return natural_benefics(self.positions)

    @cached_property
    def waxing(self) -> bool:
        return waxing_moon(self.positions)

    def aspected_signs(self, body: Body) -> list[int]:
        return graha_aspected_signs(body, self.signs[body], self.node_aspects_5_9)

    def aspects_sign(self, body: Body, sign: int) -> bool:
        return sign in self.aspected_signs(body)

    def aspects(self, body: Body, target: Point) -> bool:
        return self.aspects_sign(body, self.sign_of(target))

    # --- lunar day and mansions ---------------------------------------------------

    @cached_property
    def elongation(self) -> float:
        return (self.positions[Body.MOON] - self.positions[Body.SUN]) % 360.0

    @property
    def tithi(self) -> int:
        """1-15 in the bright half (Shukla), 16-30 in the dark half; 30 is Amavasya."""
        return int(self.elongation // 12.0) + 1

    @property
    def karana(self) -> str:
        index = int(self.elongation // 6.0)
        return FIXED_KARANAS.get(index) or MOVABLE_KARANAS[(index - 1) % 7]

    def nakshatra(self, point: Point) -> int:
        """1 (Ashwini) to 27 (Revati)."""
        return nakshatra_of(self.longitude(point)).nakshatra.index + 1

    def pada(self, point: Point) -> int:
        return nakshatra_of(self.longitude(point)).pada

    def gandanta(self, point: Point) -> bool:
        return is_gandanta(self.longitude(point))

    # --- period: dasha and transits ------------------------------------------------

    def dasha_lord(self, level: int) -> Body:
        """The running lord at ``level`` (1 = mahadasha, 2 = antardasha)."""
        if len(self.dasha) < level:
            raise MissingFactError("dasha")
        return self.dasha[level - 1]

    def transit_sign(self, body: Body) -> int:
        if self.transits is None or body not in self.transits:
            raise MissingFactError("transits")
        return int(self.transits[body] // 30.0) % 12

    def transit_house(self, body: Body, reference: Point = LAGNA) -> int:
        """House (1-12) of transiting ``body`` counted from the natal ``reference``."""
        return (self.transit_sign(body) - self.sign_of(reference)) % 12 + 1

    # --- birth facts --------------------------------------------------------------

    def require_day_birth(self) -> bool:
        if self.day_birth is None:
            raise MissingFactError("day_birth")
        return self.day_birth

    def require_gender(self) -> str:
        if self.gender is None:
            raise MissingFactError("gender")
        return self.gender
