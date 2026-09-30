"""Ashtakoota (guna milan): eight kootas from the two Moons, out of 36 points, with
the Nadi, Bhakoot and Gana doshas and their traditional exceptions.

Counts between nakshatras or signs are inclusive: the same one counts 1.
"""

from __future__ import annotations

from dataclasses import dataclass

from jyotish_engine.astro.bodies import Body
from jyotish_engine.core.dignity import Relationship, natural_relationship
from jyotish_engine.core.nakshatra import PADA_SPAN, nakshatra_of
from jyotish_engine.core.zodiac import SIGN_LORDS, Sign
from jyotish_engine.match import tables as t
from jyotish_engine.match.tables import KootaProfile
from jyotish_engine.rules.schema import Citation


@dataclass(frozen=True, slots=True)
class MoonPlacement:
    """A partner's Moon by its sidereal longitude."""

    longitude: float

    @classmethod
    def from_pada(cls, nakshatra: int, pada: int) -> MoonPlacement:
        """The middle of a nakshatra pada (0-based nakshatra, pada 1-4), for matching
        by birth star alone. The first pada of Purva Ashadha and the second of
        Shravana straddle the middle of their signs, which decides the Vashya group;
        their midpoints fall in the second half."""
        return cls((nakshatra * 4 + pada - 0.5) * PADA_SPAN)

    @property
    def sign(self) -> int:
        return min(int(self.longitude % 360.0 // 30.0), 11)

    @property
    def degrees_in_sign(self) -> float:
        return self.longitude % 360.0 - 30.0 * self.sign

    @property
    def nakshatra(self) -> int:
        return nakshatra_of(self.longitude).nakshatra.index

    @property
    def pada(self) -> int:
        return nakshatra_of(self.longitude).pada

    @property
    def lord(self) -> Body:
        return SIGN_LORDS[Sign(self.sign)]


def count(start: int, end: int, size: int) -> int:
    """Position of ``end`` counted from ``start`` inclusively (1 when equal)."""
    return (end - start) % size + 1


def lord_views(a: Body, b: Body) -> tuple[Relationship, Relationship]:
    """Natural relationship of each Moon-sign lord towards the other."""
    return natural_relationship(a, b), natural_relationship(b, a)


def lords_friendly(a: Body, b: Body) -> bool:
    """The same planet, or natural friends both ways."""
    return a is b or lord_views(a, b) == (Relationship.FRIEND, Relationship.FRIEND)


@dataclass(frozen=True, slots=True)
class KootaScore:
    name: str
    points: float
    maximum: float
    groom: str
    bride: str
    detail: str
    sources: tuple[Citation, ...]


@dataclass(frozen=True, slots=True)
class DoshaCheck:
    name: str
    present: bool
    #: The traditional exceptions that apply (each cancels the dosha).
    exceptions: tuple[str, ...] = ()
    sources: tuple[Citation, ...] = ()

    @property
    def cancelled(self) -> bool:
        return self.present and bool(self.exceptions)


@dataclass(frozen=True, slots=True)
class Ashtakoota:
    profile: KootaProfile
    kootas: tuple[KootaScore, ...]
    doshas: tuple[DoshaCheck, ...]

    @property
    def total(self) -> float:
        return sum(k.points for k in self.kootas)

    def __getitem__(self, name: str) -> KootaScore:
        return next(k for k in self.kootas if k.name == name)


def _maitri(groom: Body, bride: Body, profile: KootaProfile) -> tuple[float, str]:
    if groom is bride:
        return 5.0, f"both Moon signs ruled by {groom.value}"
    views = lord_views(groom, bride)
    key = tuple(
        sum(v is r for v in views)
        for r in (Relationship.FRIEND, Relationship.NEUTRAL, Relationship.ENEMY)
    )
    detail = (
        f"{groom.value} sees {bride.value} as {views[0].name.lower()}; "
        f"{bride.value} sees {groom.value} as {views[1].name.lower()}"
    )
    return t.MAITRI_POINTS[profile][key], detail  # type: ignore[index]


def _nadi_exceptions(groom: MoonPlacement, bride: MoonPlacement) -> tuple[str, ...]:
    same_sign, same_star = groom.sign == bride.sign, groom.nakshatra == bride.nakshatra
    found = []
    if same_sign and not same_star:
        found.append("same Moon sign, different nakshatras")
    if same_star and not same_sign:
        found.append("same nakshatra, different Moon signs")
    if same_star and same_sign and groom.pada != bride.pada:
        found.append("same nakshatra, different padas")
    if not same_sign and lords_friendly(groom.lord, bride.lord):
        found.append("Moon-sign lords the same planet or mutual friends")
    return tuple(found)


def ashtakoota(
    groom: MoonPlacement, bride: MoonPlacement, profile: KootaProfile = KootaProfile.POPULAR
) -> Ashtakoota:
    """The eight kootas for a groom's and a bride's Moon."""
    src = {name: by_profile[profile] for name, by_profile in t.SOURCES.items()}
    scores: list[KootaScore] = []

    gv, bv = t.varna(groom.sign, profile), t.varna(bride.sign, profile)
    scores.append(
        KootaScore("varna", float(gv <= bv), 1.0, gv.name.title(), bv.name.title(),
                   "the groom's varna should equal or exceed the bride's", src["varna"])
    )  # fmt: skip

    gw = t.vashya(groom.sign, groom.degrees_in_sign)
    bw = t.vashya(bride.sign, bride.degrees_in_sign)
    scores.append(
        KootaScore("vashya", t.VASHYA_POINTS[profile][bw][gw], 2.0, gw.name.title(),
                   bw.name.title(), "", src["vashya"])
    )  # fmt: skip

    from_bride = count(bride.nakshatra, groom.nakshatra, 27)
    from_groom = count(groom.nakshatra, bride.nakshatra, 27)
    good = [n % 9 not in t.TARA_BAD_REMAINDERS for n in (from_bride, from_groom)]
    scores.append(
        KootaScore("tara", 1.5 * sum(good), 3.0, f"{from_groom} from the groom",
                   f"{from_bride} from the bride",
                   "remainders of 3, 5 or 7 on dividing by 9 are inauspicious", src["tara"])
    )  # fmt: skip

    (ga, gm), (ba, bm) = t.NAKSHATRA_YONI[groom.nakshatra], t.NAKSHATRA_YONI[bride.nakshatra]
    scores.append(
        KootaScore("yoni", float(t.YONI_POINTS[ba][ga]), 4.0,
                   f"{t.YONI_ANIMALS[ga]} ({'male' if gm else 'female'})",
                   f"{t.YONI_ANIMALS[ba]} ({'male' if bm else 'female'})", "", src["yoni"])
    )  # fmt: skip

    maitri, detail = _maitri(groom.lord, bride.lord, profile)
    scores.append(
        KootaScore("graha_maitri", maitri, 5.0, groom.lord.value, bride.lord.value, detail,
                   src["graha_maitri"])
    )  # fmt: skip

    gg, bg = t.NAKSHATRA_GANA[groom.nakshatra], t.NAKSHATRA_GANA[bride.nakshatra]
    scores.append(
        KootaScore("gana", float(t.GANA_POINTS[bg][gg]), 6.0, gg.name.title(), bg.name.title(),
                   "", src["gana"])
    )  # fmt: skip

    distance = count(bride.sign, groom.sign, 12)
    bhakoot_dosha = distance in t.BHAKOOT_DOSHA_DISTANCES
    scores.append(
        KootaScore("bhakoot", 0.0 if bhakoot_dosha else 7.0, 7.0, f"sign {groom.sign + 1}",
                   f"sign {bride.sign + 1}",
                   f"the groom's Moon sign is {distance} from the bride's", src["bhakoot"])
    )  # fmt: skip

    gn, bn = t.NAKSHATRA_NADI[groom.nakshatra], t.NAKSHATRA_NADI[bride.nakshatra]
    scores.append(
        KootaScore("nadi", 0.0 if gn == bn else 8.0, 8.0, gn.name.title(), bn.name.title(), "",
                   src["nadi"])
    )  # fmt: skip

    popular = Citation(text="popular_practice", locator="Nadi dosha exceptions")
    gana_dosha = (gg is t.Gana.RAKSHASA) != (bg is t.Gana.RAKSHASA)
    doshas = (
        DoshaCheck("nadi", gn == bn, _nadi_exceptions(groom, bride) if gn == bn else (),
                   (popular, t.RAMAN)),
        DoshaCheck("bhakoot", bhakoot_dosha,
                   ("Moon-sign lords the same planet or mutual friends",)
                   if bhakoot_dosha and lords_friendly(groom.lord, bride.lord) else (),
                   (t.RAMAN,)),
        DoshaCheck("gana", gana_dosha,
                   ("the bride's nakshatra is beyond the 14th from the groom's",)
                   if gana_dosha and from_groom > 14 else (),
                   (t.RAMAN,)),
    )  # fmt: skip
    return Ashtakoota(profile, tuple(scores), doshas)
