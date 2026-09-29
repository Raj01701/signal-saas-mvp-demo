"""Generate chart-level Jyotish reference values with PyJHora (development only).

For random births it records PyJHora's sidereal positions (Lahiri, true nodes) and
the quantities derived from them: chara karakas, bhava arudhas, compound
relationships, special lagnas and upagrahas. Only numbers are written, to
``engine/tests/fixtures/chart_pyjhora.json``.

    oracle/.venv/bin/python oracle/generate_chart_fixtures.py
"""

from __future__ import annotations

import contextlib
import io
import json
import random
from datetime import UTC, datetime
from pathlib import Path

import swisseph as swe
from jhora import utils
from jhora.horoscope.chart import arudhas, charts, house
from jhora.panchanga import drik

ROOT = Path(__file__).resolve().parent.parent
EPHE = ROOT / "oracle" / "cache" / "ephe"
OUT = ROOT / "engine" / "tests" / "fixtures" / "chart_pyjhora.json"
SEED = 20261001
N_CASES = 120


def _full(entry: list[object] | tuple[object, ...]) -> float:
    sign, lon = entry
    return 30.0 * int(sign) + float(lon)


def main() -> None:
    # PyJHora's PyPI package ships no planetary data files, so Swiss Ephemeris would
    # silently fall back to the lower-precision Moshier model. Use the real files.
    swe.set_ephe_path(str(EPHE))
    drik.set_ayanamsa_mode("LAHIRI")
    rng = random.Random(SEED)
    cases = []
    for i in range(N_CASES):
        year = rng.randint(1905, 2045)
        month = rng.randint(1, 12)
        day = rng.randint(1, 28)
        hour, minute = rng.randint(0, 23), rng.randint(0, 59)
        lat = rng.uniform(-45.0, 55.0)
        # Keep places near Greenwich so that, with local time given as UTC, civil dates
        # match local solar days (PyJHora splits days by civil date).
        lon = rng.uniform(-25.0, 25.0)
        # Local time is given as UTC (timezone 0): PyJHora adds the timezone twice when
        # it takes the Sun's longitude at sunrise for special lagnas, which a zero
        # offset neutralises.
        tz = 0.0
        place = drik.Place(f"case{i}", lat, lon, tz)
        dob = drik.Date(year, month, day)
        tob = (hour, minute, 0)
        jd_local = utils.julian_day_number(dob, tob)
        with contextlib.redirect_stdout(io.StringIO()):
            pp = charts.rasi_chart(jd_local, place)
            h_to_p = utils.get_house_planet_list_from_planet_positions(pp)
            record = {
                "id": f"c{i:03d}",
                "local": [year, month, day, hour, minute],
                "tz_hours": tz,
                "lat": lat,
                "lon": lon,
                "jd_ut": jd_local - tz / 24.0,
                "positions": {str(p): _full(v) for p, v in pp},
                "karakas": [int(x) for x in house.chara_karakas(pp)],
                "arudhas": [int(x) for x in arudhas.bhava_arudhas_from_planet_positions(pp)],
                "compound": house._get_compound_relationships_of_planets(h_to_p),
                "sunrise_local_hours": drik.sunrise(jd_local, place)[0],
                "sunset_local_hours": drik.sunset(jd_local, place)[0],
                "bhava_lagna": _full(drik.bhava_lagna(jd_local, place)),
                "hora_lagna": _full(drik.hora_lagna(jd_local, place)),
                "ghati_lagna": _full(drik.ghati_lagna(jd_local, place)),
                "pranapada": _full(drik.pranapada_lagna(jd_local, place)),
                "indu_lagna": _full(drik.indu_lagna(jd_local, place)),
                "sree_lagna": _full(drik.sree_lagna(jd_local, place)),
                "solar_upagrahas": {
                    name: _full(drik.solar_upagraha_longitudes(_full(pp[1][1]), name))
                    for name in ("dhuma", "vyatipaata", "parivesha", "indrachaapa", "upaketu")
                },
                "time_upagrahas": {
                    "kala": _full(drik.kaala_longitude(dob, tob, place)),
                    "mrityu": _full(drik.mrityu_longitude(dob, tob, place)),
                    "yamaghantaka": _full(drik.yama_ghantaka_longitude(dob, tob, place)),
                    "gulika": _full(drik.gulika_longitude(dob, tob, place)),
                    "mandi": _full(drik.maandi_longitude(dob, tob, place)),
                },
            }
        cases.append(record)
    payload = {
        "generator": "oracle/generate_chart_fixtures.py",
        "reference": "PyJHora 4.8.7 (Lahiri, true nodes, true positions, Hindu sunrise)",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "seed": SEED,
        "planet_ids": (
            "L=ascendant, 0..8 = Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu, Ketu"
        ),
        "cases": cases,
    }
    OUT.write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"wrote {len(cases)} cases to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
