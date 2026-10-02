"""The year used to turn dasha periods into calendar dates."""

from __future__ import annotations

from jyotish_engine.settings import DASHA_YEAR_DAYS, DashaYear, Settings
from jyotish_engine.transit.search import mesha_sankrantis

#: Window searched on each side of the birth for the Sun's entries into Aries (days).
_SEARCH_DAYS = 370.0


def true_sidereal_year_days(birth_jd_ut: float, settings: Settings | None = None) -> float:
    """Length of the sidereal solar year containing the birth, in days.

    Measured from the Mesha sankranti before the birth to the one after it. When
    the earlier one falls outside the ephemeris, the following year is used.
    """
    after = mesha_sankrantis(birth_jd_ut, birth_jd_ut + _SEARCH_DAYS, settings)
    try:
        before = mesha_sankrantis(birth_jd_ut - _SEARCH_DAYS, birth_jd_ut, settings)
    except ValueError:
        before = []
    if before:
        return after[0] - before[-1]
    following = mesha_sankrantis(after[0] + 1.0, after[0] + _SEARCH_DAYS, settings)
    return following[0] - after[0]


def dasha_year_days(settings: Settings, birth_jd_ut: float) -> float:
    """Days in one dasha year under ``settings.dasha_year``."""
    if settings.dasha_year is DashaYear.TRUE_SIDEREAL:
        return true_sidereal_year_days(birth_jd_ut, settings)
    return DASHA_YEAR_DAYS[settings.dasha_year]
