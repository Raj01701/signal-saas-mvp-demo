"""Generate nakshatra-dasha reference tables with PyJHora (development only).

For random births (local time given as UTC, places near Greenwich) records the
Moon's sidereal longitude, the dasha year PyJHora used, and for each supported dasha
system the mahadasha and antardasha lords with their start Julian days and
durations (plus Vimshottari pratyantardashas for the first cases). Only numbers are
written, to ``engine/tests/fixtures/dashas_pyjhora.json``.

PyJHora's default year is the "true sidereal year" between the Mesha sankrantis
around the birth. Its sankranti interpolation is sometimes minutes off, so the exact
year (Swiss Ephemeris bisection, true positions, Lahiri) is recorded as well.

    oracle/.venv/bin/python oracle/generate_dasha_fixtures.py
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
from jhora.horoscope.dhasa.graha import (
    applicability,
    ashtottari,
    chathuraaseethi_sama,
    dwadasottari,
    dwisatpathi,
    panchottari,
    sataatbika,
    shastihayani,
    shattrimsa_sama,
    shodasottari,
    vimsottari,
    yogini,
)
from jhora.panchanga import drik

ROOT = Path(__file__).resolve().parent.parent
EPHE = ROOT / "oracle" / "cache" / "ephe"
OUT = ROOT / "engine" / "tests" / "fixtures" / "dashas_pyjhora.json"
SEED = 20261002
N_CASES = 40
LEVEL = const.MAHA_DHASA_DEPTH.ANTARA
N_LEVEL3_CASES = 5
SID_FLAGS = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_TRUEPOS


def _sun_sidereal(jd_ut: float) -> float:
    return float(swe.calc_ut(jd_ut, swe.SUN, SID_FLAGS)[0][0])


def _sankranti_near(jd_ut: float) -> float:
    """Exact Mesha sankranti within a day of ``jd_ut`` (bisection)."""
    low, high = jd_ut - 1.0, jd_ut + 1.0
    for _ in range(60):
        middle = 0.5 * (low + high)
        if (_sun_sidereal(middle) + 180.0) % 360.0 - 180.0 < 0.0:
            low = middle
        else:
            high = middle
    return 0.5 * (low + high)


def _exact_true_sidereal_year(jd: float, place: Any) -> float:
    before, _ = drik.previous_planet_entry_date(const.SUN_ID, jd, place, raasi=1)
    after, _ = drik.next_planet_entry_date(const.SUN_ID, jd, place, raasi=1)
    return _sankranti_near(after) - _sankranti_near(before)


def _rows(result: Any) -> list[Any]:
    if isinstance(result, tuple) and len(result) == 2 and isinstance(result[1], list):
        return list(result[1])
    return list(result)


def _jd(date_tuple: Any) -> float:
    year, month, day, hours = date_tuple[:4]
    return float(swe.julday(int(year), int(month), int(day), float(hours)))


def _normalise(rows: list[Any], jd: float) -> list[list[Any]]:
    """Compact rows: ``[lords, start]`` with the start in days from the birth (7 dp)."""
    out = []
    for row in rows:
        lords, start = row[0], row[1]
        lords = list(lords) if isinstance(lords, (list, tuple)) else [lords]
        out.append([[int(x) for x in lords], round(_jd(start) - jd, 7)])
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
        place = drik.Place(f"d{i}", lat, lon, 0.0)
        dob, tob = drik.Date(year, month, day), (hour, minute, 0)
        jd = utils.julian_day_number(dob, tob)
        record: dict[str, Any] = {"id": f"d{i:03d}", "jd_ut": jd, "lat": lat, "lon": lon}
        with contextlib.redirect_stdout(io.StringIO()):
            pp = charts.rasi_chart(jd, place)
            record["moon"] = 30.0 * pp[2][1][0] + pp[2][1][1]
            record["ascendant"] = 30.0 * pp[0][1][0] + pp[0][1][1]
            record["grahas"] = [30.0 * p[1][0] + p[1][1] for p in pp[1:10]]
            record["applicable"] = applicability.applicability_check(dob, tob, place)
            record["year_days"] = drik.dhasa_year_duration(jd=jd, place=place)
            swe.set_sid_mode(swe.SIDM_LAHIRI)
            record["true_sidereal_year_days"] = _exact_true_sidereal_year(jd, place)
            systems: dict[str, Any] = {
                "vimshottari": vimsottari.get_vimsottari_dhasa_bhukthi(
                    jd, place, dhasa_level_index=LEVEL
                ),
                "ashtottari": ashtottari.get_ashtottari_dhasa_bhukthi(
                    jd, place, dhasa_level_index=LEVEL
                ),
            }
            for name, module in {
                "yogini": yogini,
                "shodashottari": shodasottari,
                "dwadashottari": dwadasottari,
                "panchottari": panchottari,
                "shatabdika": sataatbika,
                "chaturashiti_sama": chathuraaseethi_sama,
                "dwisaptati_sama": dwisatpathi,
                "shashtihayani": shastihayani,
                "shattrimsha_sama": shattrimsa_sama,
            }.items():
                kwargs: dict[str, Any] = {"dhasa_level_index": LEVEL}
                if "round_duration" in module.get_dhasa_bhukthi.__code__.co_varnames:
                    kwargs["round_duration"] = False
                systems[name] = module.get_dhasa_bhukthi(dob, tob, place, **kwargs)
            if i < N_LEVEL3_CASES:
                systems["vimshottari_level3"] = vimsottari.get_vimsottari_dhasa_bhukthi(
                    jd, place, dhasa_level_index=const.MAHA_DHASA_DEPTH.PRATYANTARA
                )
        record["systems"] = {name: _normalise(_rows(res), jd) for name, res in systems.items()}
        cases.append(record)
    payload = {
        "generator": "oracle/generate_dasha_fixtures.py",
        "reference": "PyJHora 4.8.7 (Lahiri, true positions, default true sidereal year)",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "seed": SEED,
        "planet_ids": "0..8 = Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu, Ketu",
        "rows": "[lords from the mahadasha down, start in days from jd_ut]",
        "cases": cases,
    }
    OUT.write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"wrote {len(cases)} cases to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
