"""The ten kutas (poruthams) of South Indian matching, each agreeing or not, as
B.V. Raman describes them in *Muhurtha*, with the reliefs he allows.

Counts run from the bride's nakshatra or sign to the groom's, inclusively.
"""

from __future__ import annotations

from dataclasses import dataclass

from jyotish_engine.core.dignity import Relationship
from jyotish_engine.match import tables as t
from jyotish_engine.match.ashtakoota import MoonPlacement, count, lord_views, lords_friendly


@dataclass(frozen=True, slots=True)
class Porutham:
    name: str
    agrees: bool
    detail: str
    #: A relief that sets aside a failed kuta, if one applies.
    relieved_by: str | None = None

    @property
    def acceptable(self) -> bool:
        return self.agrees or self.relieved_by is not None


def _gana(groom: MoonPlacement, bride: MoonPlacement) -> Porutham:
    gg, bg = t.NAKSHATRA_GANA[groom.nakshatra], t.NAKSHATRA_GANA[bride.nakshatra]
    rakshasa = t.Gana.RAKSHASA
    if gg is bg:
        return Porutham("gana", True, "same gana")
    if gg is rakshasa:
        return Porutham("gana", True, "Rakshasa groom with a Deva or Manushya bride: passable")
    if bg is not rakshasa:
        return Porutham("gana", True, "Deva and Manushya")
    relief = (
        "the bride's nakshatra is beyond the 14th from the groom's"
        if count(groom.nakshatra, bride.nakshatra, 27) > 14
        else None
    )
    return Porutham("gana", False, "Deva or Manushya groom with a Rakshasa bride", relief)


def _yoni(groom: MoonPlacement, bride: MoonPlacement) -> Porutham:
    (ga, gm), (ba, bm) = t.NAKSHATRA_YONI[groom.nakshatra], t.NAKSHATRA_YONI[bride.nakshatra]
    pair = f"{t.YONI_ANIMALS[ga]} and {t.YONI_ANIMALS[ba]}"
    if frozenset((ga, ba)) in t.YONI_ENEMIES:
        return Porutham("yoni", False, f"{pair} are hostile")
    if gm and bm:
        return Porutham("yoni", False, "both male yonis")
    return Porutham("yoni", True, "same animal" if ga == ba else pair)


def _rasi(groom: MoonPlacement, bride: MoonPlacement) -> Porutham:
    distance = count(bride.sign, groom.sign, 12)
    if distance == 1:
        agrees = groom.nakshatra < bride.nakshatra
        detail = "same sign; the groom's nakshatra " + (
            "precedes" if agrees else "does not precede"
        )
    else:
        agrees = distance >= 7
        detail = f"the groom's sign is {distance} from the bride's"
    relief = None
    if not agrees and distance != 1 and lords_friendly(groom.lord, bride.lord):
        relief = "Moon-sign lords the same planet or mutual friends"
    return Porutham("rasi", agrees, detail, relief)


def _rasyadhipati(groom: MoonPlacement, bride: MoonPlacement) -> Porutham:
    if groom.lord is bride.lord:
        return Porutham("rasyadhipati", True, "same lord")
    views = lord_views(groom.lord, bride.lord)
    friends = views.count(Relationship.FRIEND)
    neutrals = views.count(Relationship.NEUTRAL)
    agrees = friends == 2 or (friends == 1 and neutrals == 1)
    detail = "friends" if friends == 2 else "friend and neutral" if agrees else "not friendly"
    return Porutham("rasyadhipati", agrees, detail)


def dashakoota(groom: MoonPlacement, bride: MoonPlacement) -> tuple[Porutham, ...]:
    """The ten kutas, with Raman's reliefs for Rajju and Stree Deergha applied last."""
    from_bride = count(bride.nakshatra, groom.nakshatra, 27)
    dina = Porutham(
        "dina", from_bride % 9 in t.DINA_GOOD_REMAINDERS, f"{from_bride} from the bride"
    )
    mahendra = Porutham("mahendra", from_bride in t.MAHENDRA_COUNTS, f"{from_bride} from the bride")
    rasi, lords = _rasi(groom, bride), _rasyadhipati(groom, bride)
    stree = Porutham("stree_deergha", from_bride > 9, f"{from_bride} from the bride")
    if not stree.agrees and rasi.agrees and lords.agrees:
        stree = Porutham(stree.name, False, stree.detail, "Rasi and Rasyadhipati kutas agree")
    vasya = Porutham(
        "vasya",
        groom.sign in t.VASYA_SIGNS[bride.sign] or bride.sign in t.VASYA_SIGNS[groom.sign],
        "one sign is amenable to the other",
    )
    same_rajju = t.NAKSHATRA_RAJJU[groom.nakshatra] is t.NAKSHATRA_RAJJU[bride.nakshatra]
    rajju = Porutham(
        "rajju", not same_rajju, f"{t.NAKSHATRA_RAJJU[groom.nakshatra].name.lower()} rajju"
        + (" for both" if same_rajju else f" and {t.NAKSHATRA_RAJJU[bride.nakshatra].name.lower()}")
    )  # fmt: skip
    if same_rajju and all(p.agrees for p in (lords, rasi, dina, mahendra)):
        rajju = Porutham(
            rajju.name, False, rajju.detail, "Rasyadhipati, Rasi, Dina and Mahendra agree"
        )
    obstructed = frozenset((groom.nakshatra, bride.nakshatra)) in t.VEDHA_PAIRS
    vedha = Porutham(
        "vedha",
        not obstructed,
        "nakshatras obstruct each other" if obstructed else "no obstruction",
    )
    return (
        dina,
        _gana(groom, bride),
        mahendra,
        stree,
        _yoni(groom, bride),
        rasi,
        lords,
        vasya,
        rajju,
        vedha,
    )
