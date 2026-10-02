"""Reference values for one birth from Swiss Ephemeris and PyJHora (oracle venv only).

    oracle/.venv/bin/python oracle/reference_chart.py 1987-10-09T12:05 29.53489 75.02898 \\
        > /tmp/reference.json
    uv run python scripts/compare_with_reference.py 1987-10-09T17:35 29.53489 75.02898 \\
        /tmp/reference.json

The time here is UTC; the comparison script takes the local time. Planets are Lahiri
sidereal (true and mean node), the ascendant uses whole-sign houses, and PyJHora gives
the Vimshottari mahadashas and the birth panchanga. Nothing here is imported by product
code (see test_license_guard.py).
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
from datetime import datetime
from pathlib import Path

import swisseph as swe
from jhora import utils
from jhora.horoscope.dhasa.graha import vimsottari
from jhora.panchanga import drik

EPHE = Path(__file__).resolve().parent / "cache" / "ephe"
BODIES = {
    "sun": swe.SUN,
    "moon": swe.MOON,
    "mars": swe.MARS,
    "mercury": swe.MERCURY,
    "jupiter": swe.JUPITER,
    "venus": swe.VENUS,
    "saturn": swe.SATURN,
}


def main(argv: list[str]) -> int:
    when, lat, lon = datetime.fromisoformat(argv[1]), float(argv[2]), float(argv[3])
    swe.set_ephe_path(str(EPHE))
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    jd = swe.julday(when.year, when.month, when.day, when.hour + when.minute / 60.0)
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
    positions = {name: swe.calc_ut(jd, body, flags)[0][0] for name, body in BODIES.items()}
    positions["rahu_true"] = swe.calc_ut(jd, swe.TRUE_NODE, flags)[0][0]
    positions["rahu_mean"] = swe.calc_ut(jd, swe.MEAN_NODE, flags)[0][0]
    positions["ascendant"] = swe.houses_ex(jd, lat, lon, b"W", swe.FLG_SIDEREAL)[1][0]
    with contextlib.redirect_stdout(io.StringIO()):
        drik.set_ayanamsa_mode("LAHIRI")
        place = drik.Place("birth", lat, lon, 0.0)
        jdj = utils.julian_day_number(
            drik.Date(when.year, when.month, when.day), (when.hour, when.minute, 0)
        )
        rows = vimsottari.get_vimsottari_dhasa_bhukthi(jdj, place, dhasa_level_index=1)
        panchanga = {
            "tithi": drik.tithi(jdj, place)[0],
            "nakshatra": drik.nakshatra(jdj, place)[0],
            "pada": drik.nakshatra(jdj, place)[1],
            "yoga": drik.yogam(jdj, place)[0],
            "karana": drik.karana(jdj, place)[0],
        }
    out = {
        "jd_ut": jd,
        "ayanamsa": swe.get_ayanamsa_ut(jd),
        "positions": positions,
        "mahadashas": [[str(r[0]), str(r[1])] for r in rows[:9]],
        "panchanga": panchanga,
    }
    sys.stdout.write(json.dumps(out) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
