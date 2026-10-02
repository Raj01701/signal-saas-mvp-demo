"""Generate transit event references with Swiss Ephemeris (development only).

Sidereal (Lahiri) sign ingresses of the grahas and stations of the planets, found by sampling
Swiss Ephemeris positions and bisecting to about 10 milliseconds. Apparent positions
and the true node, which are the engine's defaults. Only numbers are written, to
``engine/tests/fixtures/transits_swisseph.json``.

    oracle/.venv/bin/python oracle/generate_transit_fixtures.py
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import swisseph as swe

ROOT = Path(__file__).resolve().parent.parent
EPHE = ROOT / "oracle" / "cache" / "ephe"
OUT = ROOT / "engine" / "tests" / "fixtures" / "transits_swisseph.json"
FLAGS = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED

START = swe.julday(1995, 1, 1, 0.0)
END = swe.julday(2025, 1, 1, 0.0)
MOON_END = swe.julday(1997, 1, 1, 0.0)

BODIES: dict[str, tuple[int, float]] = {
    "sun": (swe.SUN, 1.0),
    "moon": (swe.MOON, 0.1),
    "mars": (swe.MARS, 0.5),
    "mercury": (swe.MERCURY, 0.25),
    "jupiter": (swe.JUPITER, 1.0),
    "venus": (swe.VENUS, 0.5),
    "saturn": (swe.SATURN, 1.0),
    "rahu": (swe.TRUE_NODE, 0.1),
}


def _position(body: int, jd_ut: float) -> tuple[float, float]:
    values = swe.calc_ut(jd_ut, body, FLAGS)[0]
    return float(values[0]), float(values[3])


def _bisect(changed: Callable[[float], bool], low: float, high: float) -> float:
    """Earliest time in (low, high] where ``changed`` becomes true."""
    while high - low > 1e-7:
        middle = 0.5 * (low + high)
        if changed(middle):
            high = middle
        else:
            low = middle
    return high


def _events(body: int, start: float, end: float, step: float) -> dict[str, list[Any]]:
    ingresses: list[list[float]] = []
    stations: list[list[float]] = []
    t = start
    lon, speed = _position(body, t)
    while t < end:
        t_next = min(t + step, end)
        lon_next, speed_next = _position(body, t_next)
        sign, sign_next = int(lon // 30), int(lon_next // 30)
        if sign != sign_next:
            when = _bisect(lambda x, s=sign: int(_position(body, x)[0] // 30) != s, t, t_next)
            ingresses.append([when, sign, int(_position(body, when)[0] // 30)])
        planet = body not in (swe.SUN, swe.MOON, swe.TRUE_NODE)
        if planet and (speed >= 0.0) != (speed_next >= 0.0):
            direct = speed < 0.0
            when = _bisect(lambda x, d=direct: (_position(body, x)[1] >= 0.0) == d, t, t_next)
            stations.append([when, _position(body, when)[0], 1 if direct else -1])
        t, lon, speed = t_next, lon_next, speed_next
    return {"ingresses": ingresses, "stations": stations}


def main() -> None:
    swe.set_ephe_path(str(EPHE))
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    bodies = {}
    for name, (body, step) in BODIES.items():
        end = MOON_END if name == "moon" else END
        bodies[name] = {"start": START, "end": end, **_events(body, START, end, step)}
    payload = {
        "generator": "oracle/generate_transit_fixtures.py",
        "reference": f"Swiss Ephemeris {swe.version} (Lahiri, apparent, true node)",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "note": "ingresses: [jd_ut, from_sign, to_sign]; stations: [jd_ut, longitude, "
        "+1 turning direct / -1 turning retrograde]",
        "bodies": bodies,
    }
    OUT.write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8")
    counts = {k: (len(v["ingresses"]), len(v["stations"])) for k, v in bodies.items()}
    print(f"wrote {OUT.relative_to(ROOT)}: {counts}")


if __name__ == "__main__":
    main()
