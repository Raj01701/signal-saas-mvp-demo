"""Transits scored by the natal Ashtakavarga.

A planet transiting a sign gives results in proportion to the bindus that sign
holds in the planet's own bhinna ashtakavarga (0-8 bindus: four is middling, fewer
weakens the transit and more strengthens it). The sarva ashtakavarga total of the
sign (28 on average) shows how supportive the sign is overall.

Each sign is also divided into eight kakshyas of 3 degrees 45 minutes, ruled in
order by Saturn, Jupiter, Mars, the Sun, Venus, Mercury, the Moon and the lagna.
While the planet moves through a kakshya whose lord contributed a bindu to that sign
in the planet's ashtakavarga, it gives its favourable results; otherwise not.

Only the seven planets have an ashtakavarga, so Rahu and Ketu are not scored.
"""

from __future__ import annotations

from dataclasses import dataclass

from jyotish_engine.astro.bodies import Body
from jyotish_engine.settings import Settings
from jyotish_engine.strength.ashtakavarga import (
    KAKSHYA_LORDS,
    KAKSHYA_SPAN,
    SEVEN,
    Ashtakavarga,
)
from jyotish_engine.transit.search import ingresses, longitude_at
from jyotish_engine.transit.timeline import sign_timeline

KAKSHYAS = round(360.0 / KAKSHYA_SPAN)  # 96 around the zodiac


@dataclass(frozen=True, slots=True)
class AshtakavargaTransit:
    """A stay of ``body`` in ``sign`` with its natal ashtakavarga score."""

    body: Body
    sign: int
    start_jd_ut: float
    end_jd_ut: float
    #: Bindus of the sign in the planet's own ashtakavarga (0-8).
    bav_bindus: int
    #: Sarva ashtakavarga bindus of the sign (0-56).
    sav_bindus: int


@dataclass(frozen=True, slots=True)
class KakshyaTransit:
    """A passage of ``body`` through one kakshya (3 degrees 45 minutes) of ``sign``."""

    body: Body
    sign: int
    #: 0-7 within the sign.
    kakshya: int
    #: The kakshya's lord: a planet name or "lagna".
    lord: str
    start_jd_ut: float
    end_jd_ut: float
    #: Whether that lord contributed a bindu to the sign in the planet's ashtakavarga.
    bindu: bool


def _check(body: Body) -> None:
    if body not in SEVEN:
        raise ValueError(f"{body.value} has no ashtakavarga; only the seven planets do")


def ashtakavarga_transits(
    natal: Ashtakavarga,
    body: Body,
    start_jd_ut: float,
    end_jd_ut: float,
    settings: Settings | None = None,
) -> list[AshtakavargaTransit]:
    """Sign stays of ``body`` over the window, each with its BAV and SAV bindus."""
    _check(body)
    return [
        AshtakavargaTransit(
            body,
            stay.sign,
            stay.start_jd_ut,
            stay.end_jd_ut,
            natal.bav[body.value][stay.sign],
            natal.sav[stay.sign],
        )
        for stay in sign_timeline(body, start_jd_ut, end_jd_ut, settings)
    ]


def kakshya_transits(
    natal: Ashtakavarga,
    body: Body,
    start_jd_ut: float,
    end_jd_ut: float,
    settings: Settings | None = None,
) -> list[KakshyaTransit]:
    """Consecutive kakshya passages of ``body`` covering ``[start_jd_ut, end_jd_ut)``."""
    _check(body)
    events = ingresses(body, start_jd_ut, end_jd_ut, settings, width=KAKSHYA_SPAN)
    if events:
        division = events[0].from_index
    else:
        division = int(longitude_at(body, start_jd_ut, settings) // KAKSHYA_SPAN) % KAKSHYAS
    passages: list[KakshyaTransit] = []
    begin = start_jd_ut
    for end, following in [(e.jd_ut, e.to_index) for e in events] + [(end_jd_ut, -1)]:
        sign, index = divmod(division, 8)
        lord = KAKSHYA_LORDS[index]
        bindu = natal.prastara[body.value][lord][sign] == 1
        passages.append(KakshyaTransit(body, sign, index, lord, begin, end, bindu))
        division, begin = following, end
    return passages
