"""Saturn's transits counted from the natal Moon: Sade Sati and its relatives.

* **Sade Sati** ("seven and a half"): Saturn in the 12th, 1st and 2nd signs from the
  Moon, about two and a half years each; the phases are called rising, peak and
  setting.
* **Ardhashtama Shani** ("half-eighth"): Saturn in the 4th from the Moon.
* **Ashtama Shani**: Saturn in the 8th from the Moon.
* **Kantaka Shani** ("thorn"): Saturn in the 4th, 7th or 10th from the Moon (South
  Indian usage; some count the Moon's own sign as well, which Sade Sati covers).

Retrograde motion can take Saturn back out of these signs for a few months. Stays
less than ``EPISODE_GAP_DAYS`` apart belong to one episode, which runs from the first
entry to the final exit; ``spans`` lists the actual stays. The reference sign can be
the lagna instead of the Moon.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from jyotish_engine.astro.bodies import Body
from jyotish_engine.settings import Settings
from jyotish_engine.transit.timeline import SignStay, house_from, sign_timeline

#: Stays closer together than this (about two years) are one episode.
EPISODE_GAP_DAYS = 730.0


class SaturnTransit(StrEnum):
    SADE_SATI = "sade_sati"
    ARDHASHTAMA = "ardhashtama"
    ASHTAMA = "ashtama"
    KANTAKA = "kantaka"


HOUSES: dict[SaturnTransit, tuple[int, ...]] = {
    SaturnTransit.SADE_SATI: (12, 1, 2),
    SaturnTransit.ARDHASHTAMA: (4,),
    SaturnTransit.ASHTAMA: (8,),
    SaturnTransit.KANTAKA: (4, 7, 10),
}

SADE_SATI_PHASES = {12: "rising", 1: "peak", 2: "setting"}


@dataclass(frozen=True, slots=True)
class TransitSpan:
    house: int  # 1-based, from the reference sign
    sign: int
    start_jd_ut: float
    end_jd_ut: float


@dataclass(frozen=True, slots=True)
class TransitEpisode:
    kind: SaturnTransit
    start_jd_ut: float
    end_jd_ut: float
    spans: tuple[TransitSpan, ...]
    #: True when the episode was already running at the start of the window
    #: (or still running at its end), so the real first entry (or exit) lies outside.
    open_start: bool
    open_end: bool


def _episodes(
    kind: SaturnTransit, stays: list[SignStay], reference_sign: int, window: tuple[float, float]
) -> list[TransitEpisode]:
    wanted = HOUSES[kind]
    groups: list[list[TransitSpan]] = []
    for stay in stays:
        house = house_from(reference_sign, stay.sign)
        if house not in wanted:
            continue
        span = TransitSpan(house, stay.sign, stay.start_jd_ut, stay.end_jd_ut)
        if groups and span.start_jd_ut - groups[-1][-1].end_jd_ut < EPISODE_GAP_DAYS:
            groups[-1].append(span)
        else:
            groups.append([span])
    return [
        TransitEpisode(
            kind,
            group[0].start_jd_ut,
            group[-1].end_jd_ut,
            tuple(group),
            open_start=group[0].start_jd_ut <= window[0],
            open_end=group[-1].end_jd_ut >= window[1],
        )
        for group in groups
    ]


def saturn_transits(
    reference_sign: int,
    start_jd_ut: float,
    end_jd_ut: float,
    settings: Settings | None = None,
    kinds: tuple[SaturnTransit, ...] = tuple(SaturnTransit),
) -> dict[SaturnTransit, list[TransitEpisode]]:
    """Episodes of each kind between the two dates, from ``reference_sign`` (0 = Aries)."""
    stays = sign_timeline(Body.SATURN, start_jd_ut, end_jd_ut, settings)
    window = (start_jd_ut, end_jd_ut)
    return {kind: _episodes(kind, stays, reference_sign, window) for kind in kinds}


def sade_sati(
    moon_sign: int, start_jd_ut: float, end_jd_ut: float, settings: Settings | None = None
) -> list[TransitEpisode]:
    return saturn_transits(moon_sign, start_jd_ut, end_jd_ut, settings, (SaturnTransit.SADE_SATI,))[
        SaturnTransit.SADE_SATI
    ]
