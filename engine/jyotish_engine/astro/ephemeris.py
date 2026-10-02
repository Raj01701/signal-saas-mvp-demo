"""Loading of NASA JPL planetary ephemerides.

Resolution order:

1. ``JYOTISH_EPHEMERIS``: explicit path to a ``.bsp`` kernel.
2. ``de440.bsp`` inside ``JYOTISH_DATA_DIR`` (default ``<repo>/data/ephemeris``).
3. ``de421.bsp`` bundled by the ``skyfield-data`` package (1899-07-28 to 2053-10-08).

The engine never extrapolates: instants outside the kernel's coverage raise
:class:`EphemerisRangeError`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

from skyfield.api import load_file
from skyfield_data import get_skyfield_data_path

from jyotish_engine.astro.bodies import Body

REPO_ROOT = Path(__file__).resolve().parents[3]

_TARGETS: dict[Body, tuple[str, ...]] = {
    Body.SUN: ("sun",),
    Body.MOON: ("moon",),
    Body.MERCURY: ("mercury", "mercury barycenter"),
    Body.VENUS: ("venus", "venus barycenter"),
    Body.MARS: ("mars barycenter", "mars"),
    Body.JUPITER: ("jupiter barycenter",),
    Body.SATURN: ("saturn barycenter",),
    Body.URANUS: ("uranus barycenter",),
    Body.NEPTUNE: ("neptune barycenter",),
    Body.PLUTO: ("pluto barycenter",),
}


def _calendar_date(jd: float) -> str:
    """Proleptic Gregorian date of a Julian day, for messages."""
    return (datetime(2000, 1, 1, 12) + timedelta(days=jd - 2451545.0)).date().isoformat()


class EphemerisRangeError(ValueError):
    """Raised when an instant falls outside the loaded kernel's coverage."""


def skyfield_data_dir() -> Path:
    """Directory holding Skyfield's offline data (bundled DE421 and IERS files)."""
    return Path(get_skyfield_data_path())


def data_dir() -> Path:
    return Path(os.environ.get("JYOTISH_DATA_DIR", REPO_ROOT / "data" / "ephemeris"))


def resolve_kernel_path() -> Path:
    explicit = os.environ.get("JYOTISH_EPHEMERIS")
    if explicit:
        path = Path(explicit)
        if not path.is_file():
            raise FileNotFoundError(f"JYOTISH_EPHEMERIS points to a missing file: {path}")
        return path
    preferred = data_dir() / "de440.bsp"
    if preferred.is_file():
        return preferred
    return skyfield_data_dir() / "de421.bsp"


@dataclass(frozen=True, slots=True)
class EphemerisInfo:
    name: str
    path: str
    jd_start: float
    jd_end: float


class Ephemeris:
    """A loaded JPL kernel plus the Skyfield vector functions the engine needs."""

    def __init__(self, path: Path) -> None:
        self.kernel: Any = load_file(str(path))
        starts = [segment.spk_segment.start_jd for segment in self.kernel.segments]
        ends = [segment.spk_segment.end_jd for segment in self.kernel.segments]
        self.info = EphemerisInfo(
            name=path.stem.upper(),
            path=str(path),
            jd_start=float(max(starts)),
            jd_end=float(min(ends)),
        )
        self.earth: Any = self.kernel["earth"]
        self._targets: dict[Body, Any] = {}
        for body, names in _TARGETS.items():
            for name in names:
                try:
                    self._targets[body] = self.kernel[name]
                    break
                except KeyError:
                    continue

    def target(self, body: Body) -> Any:
        try:
            return self._targets[body]
        except KeyError as exc:
            raise ValueError(f"{body} is not available in {self.info.name}") from exc

    def check_range(self, jd_tt: float) -> None:
        if not self.info.jd_start <= jd_tt <= self.info.jd_end:
            first, last = (_calendar_date(jd) for jd in (self.info.jd_start, self.info.jd_end))
            raise EphemerisRangeError(
                f"dates must fall between {first} and {last} with the {self.info.name} "
                f"ephemeris (requested JD(TT) {jd_tt:.5f})"
            )


@lru_cache(maxsize=1)
def get_ephemeris() -> Ephemeris:
    """Load (once) and return the configured ephemeris."""
    return Ephemeris(resolve_kernel_path())
