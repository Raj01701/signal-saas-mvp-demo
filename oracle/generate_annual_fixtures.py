"""Generate annual-chart references (development only).

For random births and years of life:

* the Varsha Pravesha (solar return) and the Tithi Pravesha, found independently
  with Swiss Ephemeris (Lahiri, apparent positions) by sampling and bisection;
* PyJHora's Patyayini dasha for the annual chart, with the krisamsas (degrees in
  sign of the lagna and seven planets) it used and its year length.

Only numbers are written, to ``engine/tests/fixtures/annual_swisseph.json``.

    oracle/.venv/bin/python oracle/generate_annual_fixtures.py
"""

from __future__ import annotations

import contextlib
import io
import json
import random
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import swisseph as swe
from jhora import const, utils
from jhora.horoscope.chart import charts
from jhora.horoscope.dhasa.annual import patyayini
from jhora.panchanga import drik

ROOT = Path(__file__).resolve().parent.parent
EPHE = ROOT / "oracle" / "cache" / "ephe"
OUT = ROOT / "engine" / "tests" / "fixtures" / "annual_swisseph.json"
SEED = 20261004
N_CASES = 40
FLAGS = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
YEAR = 365.256363


def _lon(jd_ut: float, body: int) -> float:
    return float(swe.calc_ut(jd_ut, body, FLAGS)[0][0])


def _wrap(angle: float) -> float:
    return (angle + 180.0) % 360.0 - 180.0


def _root(f: Callable[[float], float], low: float, high: float) -> float:
    """Bisect a sign change of ``f`` (continuous near the root) to ~10 ms."""
    f_low = f(low)
    while high - low > 1e-7:
        middle = 0.5 * (low + high)
        f_mid = f(middle)
        if (f_mid < 0.0) == (f_low < 0.0):
            low, f_low = middle, f_mid
        else:
            high = middle
    return 0.5 * (low + high)


def _crossings(f: Callable[[float], float], start: float, end: float, step: float) -> list[float]:
    found = []
    t, value = start, f(start)
    while t < end:
        t_next = min(t + step, end)
        v_next = f(t_next)
        if (value < 0.0) != (v_next < 0.0) and abs(value - v_next) < 180.0:
            found.append(_root(f, t, t_next))
        t, value = t_next, v_next
    return found


def _solar_return(birth: float, sun0: float, years: int) -> float:
    guess = birth + years * YEAR
    return _crossings(lambda t: _wrap(_lon(t, swe.SUN) - sun0), guess - 4, guess + 4, 0.5)[0]


def _tithi_pravesha(birth: float, sun0: float, moon0: float, years: int) -> float:
    solar_return = _solar_return(birth, sun0, years)
    sign = int(sun0 // 30.0)
    boundary = sign * 30.0

    def entry(t: float) -> float:
        return _wrap(_lon(t, swe.SUN) - boundary)

    def exit_(t: float) -> float:
        return _wrap(_lon(t, swe.SUN) - (boundary + 30.0))

    start = _crossings(entry, solar_return - 35.0, solar_return, 0.5)[-1]
    end = _crossings(exit_, solar_return, solar_return + 35.0, 0.5)[0]
    target = (moon0 - sun0) % 360.0

    def elongation(t: float) -> float:
        return _wrap(_lon(t, swe.MOON) - _lon(t, swe.SUN) - target)

    found = _crossings(elongation, start, end, 0.1)
    if found:
        return found[0]
    nearby = _crossings(elongation, solar_return - 20.0, solar_return + 20.0, 0.1)
    return min(nearby, key=lambda t: abs(t - solar_return))


def _rows(rows: list[Any], jd: float) -> list[list[Any]]:
    out = []
    for lords, start, _ in rows:
        names = ["lagna" if x == const._ascendant_symbol else int(x) for x in lords]
        year, month, day, hours = start[:4]
        start_jd = swe.julday(int(year), int(month), int(day), float(hours))
        out.append([names, round(start_jd - jd, 7)])
    return out


def main() -> None:
    swe.set_ephe_path(str(EPHE))
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    drik.set_ayanamsa_mode("LAHIRI")
    rng = random.Random(SEED)
    cases = []
    for i in range(N_CASES):
        birth = swe.julday(
            rng.randint(1930, 1995), rng.randint(1, 12), rng.randint(1, 28), rng.uniform(0.0, 24.0)
        )
        lat, lon = rng.uniform(-40.0, 55.0), rng.uniform(-25.0, 25.0)
        years = rng.randint(1, 50)
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        sun0, moon0 = _lon(birth, swe.SUN), _lon(birth, swe.MOON)
        record: dict[str, Any] = {
            "id": f"y{i:03d}",
            "birth_jd_ut": birth,
            "lat": lat,
            "lon": lon,
            "sun": sun0,
            "moon": moon0,
            "years_completed": years,
            "varsha_pravesha": _solar_return(birth, sun0, years),
            "tithi_pravesha": _tithi_pravesha(birth, sun0, moon0, years),
        }
        # Swiss Ephemeris' Delta T at each event, so times can be compared in TT
        # (future Delta T is a prediction and differs between tools by about a second).
        for key in ("varsha_pravesha", "tithi_pravesha"):
            record[f"{key}_delta_t_days"] = float(swe.deltat(record[key]))
        jd_year = record["varsha_pravesha"]
        place = drik.Place(record["id"], lat, lon, 0.0)
        with contextlib.redirect_stdout(io.StringIO()):
            pp = charts.divisional_chart(jd_year, place)[: const._pp_count_upto_saturn]
            record["patyayini_krisamsas"] = {
                ("lagna" if p == const._ascendant_symbol else str(p)): float(v[1]) for p, v in pp
            }
            record["patyayini_year_days"] = drik.dhasa_year_duration(jd=jd_year, place=place)
            record["patyayini"] = _rows(
                patyayini.get_dhasa_bhukthi(
                    jd_year, place, dhasa_level_index=const.MAHA_DHASA_DEPTH.ANTARA
                ),
                jd_year,
            )
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        cases.append(record)
    payload = {
        "generator": "oracle/generate_annual_fixtures.py",
        "reference": f"Swiss Ephemeris {swe.version} (Lahiri, apparent); PyJHora 4.8.7 (Patyayini)",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "seed": SEED,
        "planet_ids": "0..6 = Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn",
        "cases": cases,
    }
    OUT.write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"wrote {len(cases)} cases to {OUT.relative_to(ROOT)}")
    _ = utils  # imported for PyJHora's side effects on paths


if __name__ == "__main__":
    main()
