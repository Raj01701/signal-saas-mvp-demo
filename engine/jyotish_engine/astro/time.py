"""Time scales: civil UTC, UT1 and Terrestrial Time (TT).

Planet positions are computed in TT; sidereal time, and therefore the ascendant and
house cusps, depend on UT1. Skyfield supplies Delta T (TT - UT1): IERS values for the
modern era and the Stephenson, Morrison & Hohenkerk (2016) model for historical dates.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

from skyfield.api import Loader

from jyotish_engine.astro.ephemeris import skyfield_data_dir

SECONDS_PER_DAY = 86400.0
J2000_JD = 2451545.0


@lru_cache(maxsize=1)
def timescale() -> Any:
    """Return the shared Skyfield timescale (built-in Delta T and leap-second tables)."""
    return Loader(str(skyfield_data_dir()), expire=False, verbose=False).timescale(builtin=True)


@dataclass(frozen=True, slots=True)
class Instant:
    """A moment in time expressed on both the UT1 and TT scales (Julian days)."""

    jd_ut: float
    jd_tt: float

    @classmethod
    def from_utc(cls, moment: datetime) -> Instant:
        """Build an instant from a civil UTC datetime (naive values are taken as UTC)."""
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=UTC)
        t = timescale().from_datetime(moment.astimezone(UTC))
        return cls(jd_ut=float(t.ut1), jd_tt=float(t.tt))

    @classmethod
    def from_jd_ut(cls, jd_ut: float) -> Instant:
        t = timescale().ut1_jd(jd_ut)
        return cls(jd_ut=float(jd_ut), jd_tt=float(t.tt))

    @classmethod
    def from_jd_tt(cls, jd_tt: float) -> Instant:
        t = timescale().tt_jd(jd_tt)
        return cls(jd_ut=float(t.ut1), jd_tt=float(jd_tt))

    @property
    def delta_t_seconds(self) -> float:
        """TT - UT1 in seconds."""
        return (self.jd_tt - self.jd_ut) * SECONDS_PER_DAY

    @property
    def centuries_tt(self) -> float:
        """Julian centuries of TT since J2000.0."""
        return (self.jd_tt - J2000_JD) / 36525.0

    def skyfield(self) -> Any:
        """The equivalent Skyfield ``Time`` (TT-based, so Delta T stays consistent)."""
        return timescale().tt_jd(self.jd_tt)

    def utc_datetime(self) -> datetime:
        """Civil UTC datetime for this instant."""
        value: datetime = self.skyfield().utc_datetime()
        return value
