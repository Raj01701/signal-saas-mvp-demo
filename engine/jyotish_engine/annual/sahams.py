"""Tajika sahams (sensitive points), following P.V.R. Narasimha Rao's table of 36.

A saham is written A - B + C: the arc from B to A, measured on from C. When C does
not lie between B and A (going zodiacally from the sign after B's, C's sign is not
met before A's sign), one sign, 30 degrees, is added; this sign-by-sign reading of
Tajika Neelakanthi's rule is the one Rao's worked examples follow. By night most
formulas swap A and B. "House n" is the lagna's longitude plus (n - 1) x 30 degrees,
and sign lords are the planetary lords (Tajika does not use Rahu or Ketu as lords).

Sahams about disease, death, adultery and imprisonment are marked ``sensitive``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from jyotish_engine.astro.bodies import Body
from jyotish_engine.core.zodiac import SIGN_LORDS, Sign

#: A term of a saham formula: a planet name, "lagna", "house:N" (a cusp in
#: equal houses from the lagna), "lord:N" (the lord of house N), "sign_lord:P"
#: (the lord of the sign occupied by planet P), "saham:NAME", or a fixed longitude.
Term = str | float


@dataclass(frozen=True, slots=True)
class SahamRule:
    name: str
    meaning: str
    a: Term
    b: Term
    c: Term
    reverse_at_night: bool = True
    #: A different formula by night (instead of swapping A and B).
    night: tuple[Term, Term, Term] | None = None
    sensitive: bool = False


RULES: tuple[SahamRule, ...] = (
    SahamRule("punya", "fortune, merit", "moon", "sun", "lagna"),
    SahamRule("vidya", "education, learning", "sun", "moon", "lagna"),
    SahamRule("yasas", "fame", "jupiter", "saham:punya", "lagna"),
    SahamRule("mitra", "friends", "jupiter", "saham:punya", "venus"),
    SahamRule("mahatmya", "greatness", "saham:punya", "mars", "lagna"),
    SahamRule("asha", "desires", "saturn", "mars", "lagna"),
    SahamRule("samartha", "ability, enterprise", "mars", "lord:1", "lagna"),
    SahamRule("bhratri", "siblings", "jupiter", "saturn", "lagna", reverse_at_night=False),
    SahamRule("gaurava", "respect, honour", "jupiter", "moon", "sun"),
    SahamRule("pitri", "father", "saturn", "sun", "lagna"),
    SahamRule("rajya", "kingdom, authority", "saturn", "sun", "lagna"),
    SahamRule("matri", "mother", "moon", "venus", "lagna"),
    SahamRule("putra", "children", "jupiter", "moon", "lagna"),
    SahamRule("jeeva", "life", "saturn", "jupiter", "lagna"),
    SahamRule("karma", "work, deeds", "mars", "mercury", "lagna"),
    SahamRule("roga", "disease", "lagna", "moon", "lagna", reverse_at_night=False, sensitive=True),
    SahamRule("kali", "strife, misfortune", "jupiter", "mars", "lagna"),
    SahamRule("sastra", "scriptures, sciences", "jupiter", "saturn", "mercury"),
    SahamRule("bandhu", "relatives", "mercury", "moon", "lagna"),
    SahamRule(
        "mrityu", "death", "house:8", "moon", "lagna", reverse_at_night=False, sensitive=True
    ),
    SahamRule("paradesa", "foreign lands", "house:9", "lord:9", "lagna", reverse_at_night=False),
    SahamRule("artha", "money", "house:2", "lord:2", "lagna", reverse_at_night=False),
    SahamRule("paradara", "adultery", "venus", "sun", "lagna", sensitive=True),
    SahamRule("vanik", "commerce", "moon", "mercury", "lagna"),
    SahamRule(
        "karyasiddhi",
        "success in undertakings",
        "saturn",
        "sun",
        "sign_lord:sun",
        night=("saturn", "moon", "sign_lord:moon"),
    ),
    SahamRule("vivaha", "marriage", "venus", "saturn", "lagna"),
    SahamRule("santapa", "sorrow", "saturn", "moon", "house:6"),
    SahamRule("sraddha", "devotion, sincerity", "venus", "mars", "lagna"),
    SahamRule("preeti", "love, attachment", "saham:sastra", "saham:punya", "lagna"),
    SahamRule("jadya", "chronic disease", "mars", "saturn", "mercury", sensitive=True),
    SahamRule("vyapara", "business", "mars", "saturn", "lagna", reverse_at_night=False),
    SahamRule("satru", "enemies", "mars", "saturn", "lagna"),
    SahamRule("jalapatana", "crossing water", 105.0, "saturn", "lagna"),
    SahamRule("bandhana", "imprisonment", "saham:punya", "saturn", "lagna", sensitive=True),
    SahamRule("apamrityu", "untimely death", "house:8", "mars", "lagna", sensitive=True),
    SahamRule("labha", "gains", "house:11", "lord:11", "lagna", reverse_at_night=False),
)
BY_NAME = {rule.name: rule for rule in RULES}


@dataclass(frozen=True, slots=True)
class Saham:
    name: str
    meaning: str
    longitude: float
    sensitive: bool


def _sign(longitude: float) -> int:
    return int(longitude % 360.0 // 30.0)


def between(b: float, a: float, c: float) -> bool:
    """Whether C's sign is met going zodiacally from the sign after B's to A's sign."""
    sign_a, sign_b, sign_c = _sign(a), _sign(b), _sign(c)
    for step in range(1, 12):
        sign = (sign_b + step) % 12
        if sign == sign_c:
            return True
        if sign == sign_a:
            return False
    return False


def saham_longitude(a: float, b: float, c: float) -> float:
    """A - B + C, plus one sign when C is not between B and A.

    When C is the same point as A (Roga: Lagna - Moon + Lagna) it lies on the arc by
    definition, and no sign is added.
    """
    value = a - b + c
    if c != a and not between(b, a, c):
        value += 30.0
    return value % 360.0


class _Resolver:
    def __init__(self, lagna: float, sidereal: Mapping[Body, float], by_day: bool) -> None:
        self.lagna = lagna % 360.0
        self.sidereal = sidereal
        self.by_day = by_day
        self.sahams: dict[str, float] = {}

    def lord_of_sign(self, longitude: float) -> Body:
        return SIGN_LORDS[Sign(_sign(longitude))]

    def term(self, term: Term) -> float:
        if isinstance(term, float):
            return term
        kind, _, value = term.partition(":")
        if term == "lagna":
            return self.lagna
        if kind == "house":
            return (self.lagna + (int(value) - 1) * 30.0) % 360.0
        if kind == "lord":
            house_sign = self.lagna + (int(value) - 1) * 30.0
            return self.sidereal[self.lord_of_sign(house_sign)]
        if kind == "sign_lord":
            return self.sidereal[self.lord_of_sign(self.sidereal[Body(value)])]
        if kind == "saham":
            return self.saham(BY_NAME[value])
        return self.sidereal[Body(term)]

    def formula(self, rule: SahamRule) -> tuple[Term, Term, Term]:
        a, b, c = rule.a, rule.b, rule.c
        if rule.name == "samartha" and self.lord_of_sign(self.lagna) is Body.MARS:
            a, b = "jupiter", "mars"  # Mars owns the lagna: Jupiter - Mars + Lagna
        if not self.by_day:
            if rule.night is not None:
                return rule.night
            if rule.reverse_at_night:
                a, b = b, a
        return a, b, c

    def saham(self, rule: SahamRule) -> float:
        if rule.name not in self.sahams:
            a, b, c = (self.term(t) for t in self.formula(rule))
            self.sahams[rule.name] = saham_longitude(a, b, c)
        return self.sahams[rule.name]


def compute_sahams(lagna: float, sidereal: Mapping[Body, float], by_day: bool) -> list[Saham]:
    """The 36 sahams of a chart from its lagna and sidereal planet longitudes."""
    resolver = _Resolver(lagna, sidereal, by_day)
    return [Saham(rule.name, rule.meaning, resolver.saham(rule), rule.sensitive) for rule in RULES]
