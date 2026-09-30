"""When each nakshatra dasha applies (BPHS, chapter 46, "Conditional dashas").

Vimshottari and Yogini apply to every chart. The other systems are prescribed for
particular births; the rules follow BPHS as read by P.V.R. Narasimha Rao (*Vedic
Astrology: An Integrated Approach*), which Jagannatha Hora also uses. Signs and
houses are whole-sign; horas are Parashara horas (Sun's hora: the first half of an
odd sign or the second half of an even sign). In the same reading, Scorpio and
Aquarius are ruled by the stronger of their two co-lords (Mars or Ketu, Saturn or
Rahu; see ``special.arudha.stronger_co_lord``).

Some translations pair Shodashottari's pakshas and horas the other way round; the
rule text is returned with the verdict so the reading is always visible.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from jyotish_engine.astro.bodies import Body
from jyotish_engine.core.varga import varga_sign
from jyotish_engine.core.zodiac import Sign
from jyotish_engine.dasha.nakshatra import NakshatraDasha
from jyotish_engine.special.arudha import stronger_co_lord

KENDRAS = (0, 3, 6, 9)
TRIKONAS = (0, 4, 8)


@dataclass(frozen=True, slots=True)
class Applicability:
    system: NakshatraDasha
    applicable: bool | None  # None when it cannot be decided (no sunrise at the poles)
    rule: str


def _sign(longitude: float) -> int:
    return int(longitude // 30.0) % 12


def _house_from(reference: int, sign: int) -> int:
    """0-based house of ``sign`` counted from ``reference``."""
    return (sign - reference) % 12


def in_sun_hora(longitude: float) -> bool:
    return varga_sign(longitude, 2) is Sign.LEO


def shukla_paksha(sun: float, moon: float) -> bool:
    """Waxing half of the lunar month: the Moon is less than 180 degrees ahead."""
    return (moon - sun) % 360.0 < 180.0


def applicability(
    ascendant: float,
    sidereal: Mapping[Body, float],
    born_during_day: bool | None,
) -> list[Applicability]:
    """Which nakshatra dashas apply to a chart, with the rule used for each."""
    lagna = _sign(ascendant)
    positions = dict(sidereal)
    signs = {body: _sign(lon) for body, lon in positions.items()}
    lagna_lord = stronger_co_lord(Sign(lagna), positions)
    seventh_lord = stronger_co_lord(Sign((lagna + 6) % 12), positions)
    tenth_lord = stronger_co_lord(Sign((lagna + 9) % 12), positions)
    rahu_from_lord = _house_from(signs[lagna_lord], signs[Body.RAHU])
    sun_hora = in_sun_hora(ascendant)
    shukla = shukla_paksha(sidereal[Body.SUN], sidereal[Body.MOON])

    day_rule: bool | None = None
    if born_during_day is not None:
        day_rule = sun_hora if born_during_day else not sun_hora

    return [
        Applicability(NakshatraDasha.VIMSHOTTARI, True, "Applies to every chart."),
        Applicability(NakshatraDasha.YOGINI, True, "Applies to every chart."),
        Applicability(
            NakshatraDasha.ASHTOTTARI,
            (rahu_from_lord in KENDRAS or rahu_from_lord in TRIKONAS) and signs[Body.RAHU] != lagna,
            "Rahu in a kendra or trikona from the lagna lord, but not in the lagna.",
        ),
        Applicability(
            NakshatraDasha.SHODASHOTTARI,
            sun_hora == shukla,
            "Lagna in the Sun's hora in Shukla paksha, or in the Moon's hora in Krishna paksha.",
        ),
        Applicability(
            NakshatraDasha.DWADASHOTTARI,
            varga_sign(ascendant, 9) in (Sign.TAURUS, Sign.LIBRA),
            "Lagna in a navamsa of Venus (Taurus or Libra).",
        ),
        Applicability(
            NakshatraDasha.PANCHOTTARI,
            varga_sign(ascendant, 12) is Sign.CANCER,
            "Lagna in the Cancer dwadashamsa.",
        ),
        Applicability(
            NakshatraDasha.SHATABDIKA,
            varga_sign(ascendant, 9) == Sign(lagna),
            "Lagna vargottama (same sign in the rashi and navamsa).",
        ),
        Applicability(
            NakshatraDasha.CHATURASHITI_SAMA,
            _house_from(lagna, signs[tenth_lord]) == 9,
            "The 10th lord in the 10th house.",
        ),
        Applicability(
            NakshatraDasha.DWISAPTATI_SAMA,
            _house_from(lagna, signs[lagna_lord]) == 6 or signs[seventh_lord] == lagna,
            "The lagna lord in the 7th house, or the 7th lord in the lagna.",
        ),
        Applicability(
            NakshatraDasha.SHASHTIHAYANI,
            signs[Body.SUN] == lagna,
            "The Sun in the lagna.",
        ),
        Applicability(
            NakshatraDasha.SHATTRIMSHA_SAMA,
            day_rule,
            "Born by day with the lagna in the Sun's hora, or by night with the lagna "
            "in the Moon's hora.",
        ),
    ]
