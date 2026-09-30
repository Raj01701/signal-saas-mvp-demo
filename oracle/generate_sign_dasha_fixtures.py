"""Generate Jaimini sign-dasha reference tables with PyJHora (development only).

For random births (local time given as UTC, places near Greenwich) records the
sidereal ascendant and graha longitudes, the dasha year PyJHora used, and:

* Chara dasha, K.N. Rao method: mahadasha signs with start times;
* Narayana dasha (rashi chart): mahadashas and antardashas, both cycles.

Only numbers are written, to ``engine/tests/fixtures/sign_dashas_pyjhora.json``.

    oracle/.venv/bin/python oracle/generate_sign_dasha_fixtures.py
"""

from __future__ import annotations

import contextlib
import io
import json
import random
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import swisseph as swe
from jhora import const, utils
from jhora.horoscope.chart import charts
from jhora.horoscope.dhasa.raasi import chara, narayana
from jhora.panchanga import drik

ROOT = Path(__file__).resolve().parent.parent
EPHE = ROOT / "oracle" / "cache" / "ephe"
OUT = ROOT / "engine" / "tests" / "fixtures" / "sign_dashas_pyjhora.json"
SEED = 20261003
N_CASES = 60


def _jd(date_tuple: Any) -> float:
    year, month, day, hours = date_tuple[:4]
    return float(swe.julday(int(year), int(month), int(day), float(hours)))


def _rows(rows: list[Any], jd: float) -> list[list[Any]]:
    """Compact rows: ``[signs, start]`` with the start in days from the birth (7 dp)."""
    out = []
    for row in rows:
        signs, start = row[0], row[1]
        signs = list(signs) if isinstance(signs, (list, tuple)) else [signs]
        out.append([[int(s) for s in signs], round(_jd(start) - jd, 7)])
    return out


def main() -> None:
    swe.set_ephe_path(str(EPHE))
    drik.set_ayanamsa_mode("LAHIRI")
    rng = random.Random(SEED)
    cases = []
    for i in range(N_CASES):
        year = rng.randint(1930, 2020)
        month, day = rng.randint(1, 12), rng.randint(1, 28)
        hour, minute = rng.randint(0, 23), rng.randint(0, 59)
        lat, lon = rng.uniform(-40.0, 55.0), rng.uniform(-25.0, 25.0)
        place = drik.Place(f"s{i}", lat, lon, 0.0)
        dob, tob = drik.Date(year, month, day), (hour, minute, 0)
        jd = utils.julian_day_number(dob, tob)
        with contextlib.redirect_stdout(io.StringIO()):
            pp = charts.rasi_chart(jd, place)
            record: dict[str, Any] = {
                "id": f"s{i:03d}",
                "jd_ut": jd,
                "ascendant": 30.0 * pp[0][1][0] + pp[0][1][1],
                "grahas": [30.0 * p[1][0] + p[1][1] for p in pp[1:10]],
                "year_days": drik.dhasa_year_duration(jd=jd, place=place),
            }
            record["chara_kn_rao"] = _rows(
                chara.get_dhasa_antardhasa(
                    dob,
                    tob,
                    place,
                    chara_method=const.CHARA_TYPE.KN_RAO,
                    dhasa_level_index=const.MAHA_DHASA_DEPTH.MAHA_DHASA_ONLY,
                    round_duration=False,
                ),
                jd,
            )
            record["narayana"] = _rows(
                narayana.narayana_dhasa_for_rasi_chart(
                    dob,
                    tob,
                    place,
                    dhasa_level_index=const.MAHA_DHASA_DEPTH.ANTARA,
                    round_duration=False,
                ),
                jd,
            )
        cases.append(record)
    payload = {
        "generator": "oracle/generate_sign_dasha_fixtures.py",
        "reference": "PyJHora 4.8.7 (Lahiri, true positions, default true sidereal year)",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "seed": SEED,
        "planet_ids": "0..8 = Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu, Ketu",
        "rows": "[signs from the mahadasha down (0 = Aries), start in days from jd_ut]",
        "cases": cases,
    }
    OUT.write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"wrote {len(cases)} cases to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
