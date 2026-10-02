"""Further timing techniques the prediction timeline combines, each from its school.

- **Divisional chart** (Parashara): a dasha lord that rules or occupies the domain's
  house in the domain's varga (D9 for marriage, D10 for career ...) delivers it more
  surely; K.N. Rao times marriage and career from the D9 and the D10 as well as the D1.
- **Chara dasha** (Jaimini, as taught by K.N. Rao): the running sign periods support a
  domain when they hold or aspect, by sign, its Jaimini karaka (the Darakaraka for
  marriage, the Amatyakaraka for career ...), its house, its house lord and, for
  marriage and career, the Upapada and the tenth arudha. Reading two dasha systems
  together narrows the margin of error.
- **KP** (K.S. Krishnamurti): an event comes in the periods of planets that signify its
  group of houses (marriage 2, 7, 11; job 2, 6, 10, 11; children 2, 5, 11 ...), read
  from Placidus cusps, occupation, ownership and star lords.
- **Ashtakavarga** (BPHS, Phaladeepika): a transit gives its result in proportion to
  the planet's own bindus in the sign it crosses (4 of 8 is the middle) and to that
  sign's sarvashtakavarga (28 is the average).
- **Double transit on the lord** (K.N. Rao): Saturn as well as Jupiter influencing the
  natal sign of the domain's house lord.

Each technique can be switched off in :class:`TimingModel`, so the Accuracy Lab can
measure what it adds on recorded events.
"""

from __future__ import annotations

import bisect
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from jyotish_engine.astro.bodies import GRAHAS, Body
from jyotish_engine.astro.houses import HouseSystem, chart_angles, quadrant_cusps
from jyotish_engine.astro.time import Instant
from jyotish_engine.core.aspects import rashi_aspects
from jyotish_engine.core.zodiac import SIGN_LORDS, Sign
from jyotish_engine.dasha.sign import SignDasha, sign_mahadashas, sign_sub_periods
from jyotish_engine.kp.significators import significators
from jyotish_engine.models import ChartResult
from jyotish_engine.predict.domains import DomainSpec, karakas
from jyotish_engine.rules.schema import Domain, ordinal
from jyotish_engine.special.karakas import Karaka


@dataclass(frozen=True, slots=True)
class TimingModel:
    """The techniques the timeline combines beyond Vimshottari, Yogini and transits."""

    #: The dasha lord's link to the domain in the domain's divisional chart.
    varga: bool = True
    #: Jaimini Chara dasha as a further timing system.
    chara: bool = True
    #: KP: the running Vimshottari lords signify the event's group of houses.
    kp: bool = True
    #: Jupiter's and Saturn's transits weighed by Ashtakavarga bindus.
    ashtakavarga: bool = True
    #: Saturn on the house lord's natal sign, with Jupiter (K.N. Rao).
    saturn_on_lord: bool = True

    @property
    def systems(self) -> int:
        """How many dasha systems can agree with Vimshottari (Yogini always can)."""
        return 1 + self.chara + self.kp


#: The model before these techniques: Vimshottari, Yogini and the slow transits only.
CLASSIC = TimingModel(varga=False, chara=False, kp=False, ashtakavarga=False, saturn_on_lord=False)
FULL = TimingModel()

#: KP house groups: the houses an event's dasha lords must signify.
KP_GROUPS: dict[Domain, tuple[int, ...]] = {
    Domain.CAREER: (2, 6, 10, 11),
    Domain.MARRIAGE: (2, 7, 11),
    Domain.CHILDREN: (2, 5, 11),
    Domain.WEALTH: (2, 6, 11),
    Domain.PROPERTY: (4, 11, 12),
    Domain.EDUCATION: (4, 9, 11),
    Domain.SPIRITUALITY: (5, 9, 12),
    Domain.HEALTH: (6, 8, 12),
    Domain.TRAVEL: (3, 9, 12),
}
#: Jaimini's chara karakas for each domain.
JAIMINI_KARAKAS: dict[Domain, tuple[Karaka, ...]] = {
    Domain.MARRIAGE: (Karaka.DARA,),
    Domain.CAREER: (Karaka.AMATYA,),
    Domain.CHILDREN: (Karaka.PUTRA,),
    Domain.PROPERTY: (Karaka.MATRI,),
    Domain.PARENTS: (Karaka.MATRI, Karaka.PITRI),
    Domain.SPIRITUALITY: (Karaka.ATMA,),
}
#: Arudhas (1-12) that carry a domain: the Upapada for marriage, the A10 for career.
ARUDHAS: dict[Domain, tuple[int, ...]] = {Domain.MARRIAGE: (12,), Domain.CAREER: (10,)}
ARUDHA_NAMES = {12: "the Upapada", 10: "the tenth arudha"}
KARAKA_NAMES = {
    Karaka.ATMA: "Atmakaraka",
    Karaka.AMATYA: "Amatyakaraka",
    Karaka.MATRI: "Matrikaraka",
    Karaka.PITRI: "Pitrikaraka",
    Karaka.PUTRA: "Putrakaraka",
    Karaka.DARA: "Darakaraka",
}
#: Divisional charts read by houses from their own lagna (D2 and D30 are not).
VARGA_LABELS = {
    4: "chaturthamsa (D4)",
    7: "saptamsa (D7)",
    9: "navamsa (D9)",
    10: "dashamsa (D10)",
    12: "dwadashamsa (D12)",
    20: "vimshamsa (D20)",
    24: "chaturvimshamsa (D24)",
}


def _name(body: Body) -> str:
    return body.value.title()


def _sign(sign: int) -> str:
    return Sign(sign).name.title()


def varga_parts(chart: ChartResult, spec: DomainSpec, body: Body) -> list[tuple[float, str]]:
    """How ``body`` links to the domain inside the domain's divisional chart."""
    label = VARGA_LABELS.get(spec.varga or 0)
    varga = next((v for v in chart.vargas if v.division == spec.varga), None)
    if label is None or varga is None:
        return []
    lagna = int(varga.ascendant.sign)
    placed = varga.grahas.get(body)
    parts: list[tuple[float, str]] = []
    for house in spec.primary:
        sign = (lagna + house - 1) % 12
        if SIGN_LORDS[Sign(sign)] is body:
            parts.append((0.35, f"rules the {ordinal(house)} house of the {label}"))
        if placed is not None and int(placed.sign) == sign:
            parts.append((0.3, f"occupies the {ordinal(house)} house of the {label}"))
    if SIGN_LORDS[Sign(lagna)] is body:
        parts.append((0.2, f"rules the lagna of the {label}"))
    return parts


@dataclass(frozen=True, slots=True)
class Target:
    """A sign the Chara dasha signs should hold or aspect, and what it stands for."""

    sign: int
    label: str
    #: A planet holds it (the dasha sign must hold or aspect the planet).
    planet: bool


def chara_targets(chart: ChartResult, spec: DomainSpec, gender: str | None) -> list[Target]:
    """The karakas, houses, house lords and arudhas a domain's Chara dashas look to."""
    signs = {g.body: int(g.sign) for g in chart.grahas if g.body in GRAHAS}
    lagna = int(chart.ascendant.sign)
    out: list[Target] = []
    for karaka in JAIMINI_KARAKAS.get(spec.domain, ()):
        body = chart.special.karakas.get(karaka)
        if body is not None:
            out.append(Target(signs[body], f"the {KARAKA_NAMES[karaka]} {_name(body)}", True))
    for body in karakas(spec, gender):
        out.append(Target(signs[body], _name(body), True))
    for house in spec.primary:
        sign = (lagna + house - 1) % 12
        out.append(Target(sign, f"the {ordinal(house)} house", False))
        lord = SIGN_LORDS[Sign(sign)]
        out.append(Target(signs[lord], f"the {ordinal(house)} lord {_name(lord)}", True))
    for arudha in ARUDHAS.get(spec.domain, ()):
        sign = int(chart.special.arudhas[arudha - 1])
        out.append(Target(sign, f"{ARUDHA_NAMES[arudha]} ({_sign(sign)})", False))
    return out


def chara_support(sign: int, targets: Sequence[Target]) -> tuple[float, list[str]]:
    """How strongly one Chara dasha sign supports a domain (0-1), and how."""
    value = 0.0
    labels: list[str] = []
    for target in targets:
        if target.sign == sign:
            value += 0.5
            labels.append(("holds " if target.planet else "is ") + target.label)
        elif rashi_aspects(sign, target.sign):
            value += 0.25
            labels.append("aspects " + target.label)
    return min(1.0, value), labels


class CharaTiming:
    """The running Chara dasha and antardasha signs, month by month."""

    def __init__(self, chart: ChartResult, until_jd: float) -> None:
        sidereal = {g.body: g.sidereal_longitude for g in chart.grahas if g.body in GRAHAS}
        mahadashas = sign_mahadashas(
            SignDasha.CHARA,
            chart.ascendant.sidereal_longitude,
            sidereal,
            chart.time.jd_ut,
            chart.dashas.year_days,
        )
        self.periods = [
            sub
            for period in mahadashas
            if period.start_jd < until_jd and period.end_jd > period.start_jd
            for sub in sign_sub_periods(SignDasha.CHARA, period, sidereal)
        ]
        self.starts = [p.start_jd for p in self.periods]

    def at(self, jd: float) -> tuple[int, int]:
        """The (mahadasha, antardasha) signs running at ``jd``."""
        period = self.periods[max(0, bisect.bisect_right(self.starts, jd) - 1)]
        return period.signs[0], period.signs[-1]


def chara_value(signs: tuple[int, int], targets: Sequence[Target]) -> float:
    """Support from the running Chara mahadasha and antardasha signs together (0-1)."""
    return 0.5 * chara_support(signs[0], targets)[0] + 0.5 * chara_support(signs[1], targets)[0]


def chara_label(signs: tuple[int, int], targets: Sequence[Target]) -> str:
    parts = []
    for level, sign in zip(("mahadasha", "antardasha"), signs, strict=True):
        _, labels = chara_support(sign, targets)
        if labels:
            parts.append(f"{level} of {_sign(sign)} " + ", ".join(labels))
    return "Chara dasha " + "; ".join(parts) if parts else ""


def kp_houses(chart: ChartResult) -> dict[Body, frozenset[int]]:
    """The houses each graha signifies in KP, from Placidus cusps of the birth moment."""
    instant = Instant(jd_ut=chart.time.jd_ut, jd_tt=chart.time.jd_tt)
    place = chart.birth.place
    angles = chart_angles(instant, place.latitude, place.longitude)
    tropical = quadrant_cusps(HouseSystem.PLACIDUS, angles).cusps
    cusps = [(c - chart.ayanamsa.true) % 360.0 for c in tropical]
    positions = {g.body: g.sidereal_longitude for g in chart.grahas if g.body in GRAHAS}
    found = significators(positions, cusps)
    return {body: frozenset(found.houses_of(body)) for body in GRAHAS}


def kp_value(
    houses: Mapping[Body, frozenset[int]],
    group: tuple[int, ...],
    chain: Sequence[Body],
    weights: Sequence[float],
) -> float:
    """Weighted share of the event's houses that the running dasha lords signify (0-1)."""
    wanted = set(group)
    return sum(
        weight * len(houses[lord] & wanted) / len(wanted)
        for weight, lord in zip(weights, chain, strict=False)
    )


def kp_label(
    houses: Mapping[Body, frozenset[int]], group: tuple[int, ...], chain: Sequence[Body]
) -> str:
    parts = []
    for lord in dict.fromkeys(chain):
        signified = sorted(houses[lord] & set(group))
        if signified:
            parts.append(f"{_name(lord)} signifies houses {', '.join(map(str, signified))}")
    joined = ", ".join(map(str, group))
    return f"KP (houses {joined}): " + "; ".join(parts) if parts else ""


def bindu_factor(bav: Mapping[str, tuple[int, ...]], body: Body, sign: int) -> float:
    """A transit's strength from the planet's own bindus in the sign (0.5 to 1.5; 4 is 1)."""
    return 0.5 + bav[body.value][sign] / 8.0


def sav_factor(sav: tuple[int, ...], sign: int) -> float:
    """A sign's sarvashtakavarga as a multiplier around the average of 28 (0.8 to 1.2)."""
    return min(1.2, max(0.8, 1.0 + (sav[sign] - 28) / 40.0))
