"""Sign timelines: which sign each graha occupies, and from when to when."""

from __future__ import annotations

from dataclasses import dataclass

from jyotish_engine.astro.bodies import Body
from jyotish_engine.settings import Settings
from jyotish_engine.transit.search import Motion, longitude_at, sign_ingresses


@dataclass(frozen=True, slots=True)
class SignStay:
    """A stay of ``body`` in ``sign`` (0 = Aries), clipped to the requested window."""

    body: Body
    sign: int
    start_jd_ut: float
    end_jd_ut: float
    #: How the stay began: True if by retrograde motion, None if before the window.
    entered_retrograde: bool | None

    def contains(self, jd_ut: float) -> bool:
        return self.start_jd_ut <= jd_ut < self.end_jd_ut


def sign_at(body: Body, jd_ut: float, settings: Settings | None = None) -> int:
    return int(longitude_at(body, jd_ut, settings) // 30.0) % 12


def sign_timeline(
    body: Body, start_jd_ut: float, end_jd_ut: float, settings: Settings | None = None
) -> list[SignStay]:
    """Consecutive sign stays covering ``[start_jd_ut, end_jd_ut)`` exactly."""
    events = sign_ingresses(body, start_jd_ut, end_jd_ut, settings)
    sign = events[0].from_index if events else sign_at(body, start_jd_ut, settings)
    stays: list[SignStay] = []
    begin, entered = start_jd_ut, None
    for event in events:
        stays.append(SignStay(body, sign, begin, event.jd_ut, entered))
        sign, begin = event.to_index, event.jd_ut
        entered = event.motion is Motion.RETROGRADE
    stays.append(SignStay(body, sign, begin, end_jd_ut, entered))
    return stays


def house_from(reference_sign: int, sign: int) -> int:
    """1-based house of ``sign`` counted from ``reference_sign`` (which is house 1)."""
    return (sign - reference_sign) % 12 + 1
