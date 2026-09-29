"""Generate astronomy reference fixtures with Swiss Ephemeris (development only).

Runs inside the isolated oracle virtualenv (``oracle/.venv``), never in the product
environment. Only the resulting numbers are committed, to
``engine/tests/fixtures/astro_swisseph.json``.

Usage (from the repository root):

    oracle/.venv/bin/python oracle/generate_astro_fixtures.py

The corpus is deterministic: 400 random instants between 1900 and 2050 at latitudes
from -60 to +65, plus hand-picked edge cases (reference epochs, sign boundaries,
high latitudes).
"""

from __future__ import annotations

import json
import random
from datetime import UTC, datetime
from pathlib import Path

import swisseph as swe

ROOT = Path(__file__).resolve().parent.parent
EPHE = ROOT / "oracle" / "cache" / "ephe"
OUT = ROOT / "engine" / "tests" / "fixtures" / "astro_swisseph.json"

SEED = 20260929
N_RANDOM = 400
JD_1900 = 2415020.5  # 1900-01-01 00:00 UT
JD_2051 = 2469807.5  # 2051-01-01 00:00 UT

BODIES = {
    "sun": swe.SUN,
    "moon": swe.MOON,
    "mercury": swe.MERCURY,
    "venus": swe.VENUS,
    "mars": swe.MARS,
    "jupiter": swe.JUPITER,
    "saturn": swe.SATURN,
    "uranus": swe.URANUS,
    "neptune": swe.NEPTUNE,
    "pluto": swe.PLUTO,
    "mean_node": swe.MEAN_NODE,
    "true_node": swe.TRUE_NODE,
}

# Sidereal modes recorded for calibration and validation (Swiss Ephemeris ids).
SIDEREAL_MODES = {
    "fagan_bradley": swe.SIDM_FAGAN_BRADLEY,
    "lahiri": swe.SIDM_LAHIRI,
    "raman": swe.SIDM_RAMAN,
    "krishnamurti": swe.SIDM_KRISHNAMURTI,
    "yukteshwar": swe.SIDM_YUKTESHWAR,
    "jn_bhasin": swe.SIDM_JN_BHASIN,
    "true_citra": swe.SIDM_TRUE_CITRA,
    "true_revati": swe.SIDM_TRUE_REVATI,
    "true_pushya": swe.SIDM_TRUE_PUSHYA,
    "lahiri_1940": swe.SIDM_LAHIRI_1940,
    "lahiri_vp285": swe.SIDM_LAHIRI_VP285,
    "krishnamurti_vp291": swe.SIDM_KRISHNAMURTI_VP291,
    "lahiri_icrc": swe.SIDM_LAHIRI_ICRC,
}

HOUSE_SYSTEMS = {"placidus": b"P", "porphyry": b"O", "equal": b"A", "sripati": b"S"}


def _case_times(rng: random.Random) -> list[tuple[str, float, float, float, float]]:
    """Return (id, jd_ut, latitude, longitude, altitude_m) tuples."""
    cases: list[tuple[str, float, float, float, float]] = []
    for i in range(N_RANDOM):
        jd = rng.uniform(JD_1900, JD_2051)
        lat = rng.uniform(-60.0, 65.0)
        lon = rng.uniform(-180.0, 180.0)
        alt = rng.choice([0.0, 0.0, 10.0, 200.0, 920.0, 2200.0])
        cases.append((f"r{i:03d}", jd, lat, lon, alt))
    # Hand-picked edge cases.
    edge = [
        ("j2000", 2451545.0, 28.6139, 77.2090, 216.0),  # J2000.0, New Delhi
        ("lahiri_epoch", 2435553.5, 22.5726, 88.3639, 9.0),  # 1956-03-21, Kolkata
        ("mumbai_1950", swe.julday(1950, 6, 15, 1.65), 19.0760, 72.8777, 14.0),
        ("chennai_1975", swe.julday(1975, 1, 26, 23.9), 13.0827, 80.2707, 6.0),
        ("new_york_1969", swe.julday(1969, 7, 20, 20.3), 40.7128, -74.0060, 10.0),
        ("london_1958", swe.julday(1958, 3, 3, 12.0), 51.5074, -0.1278, 11.0),
        ("sydney_2031", swe.julday(2031, 11, 14, 6.2), -33.8688, 151.2093, 58.0),
        ("reykjavik_1999", swe.julday(1999, 12, 21, 11.5), 64.1466, -21.9426, 30.0),
        ("tromso_high_lat", swe.julday(2010, 6, 21, 12.0), 69.6492, 18.9553, 10.0),
        ("longyearbyen", swe.julday(1995, 1, 5, 8.0), 78.2232, 15.6267, 10.0),
        ("start_1900", JD_1900 + 0.25, 0.0, 0.0, 0.0),
        ("end_2050", JD_2051 - 0.3, -45.0, 170.0, 0.0),
    ]
    return cases + edge


def _positions(jd_tt: float) -> dict[str, list[float]]:
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    out: dict[str, list[float]] = {}
    for name, pid in BODIES.items():
        xx, _ = swe.calc(jd_tt, pid, flags)
        out[name] = [xx[0], xx[1], xx[2], xx[3]]  # lon, lat, dist_au, lon_speed
    return out


def _ayanamsas(jd_tt: float) -> tuple[dict[str, float], dict[str, float]]:
    mean: dict[str, float] = {}
    true: dict[str, float] = {}
    for name, mode in SIDEREAL_MODES.items():
        swe.set_sid_mode(mode, 0, 0)
        true[name] = swe.get_ayanamsa_ex(jd_tt, swe.FLG_SWIEPH)[1]
        mean[name] = swe.get_ayanamsa_ex(jd_tt, swe.FLG_SWIEPH | swe.FLG_NONUT)[1]
    return mean, true


def _houses(jd_ut: float, lat: float, lon: float) -> dict[str, object]:
    out: dict[str, object] = {}
    for name, code in HOUSE_SYSTEMS.items():
        try:
            cusps, ascmc = swe.houses_ex(jd_ut, lat, lon, code)
            out[name] = {"cusps": list(cusps[:12]), "ok": True}
        except swe.Error as exc:  # Placidus fails at polar latitudes
            out[name] = {"cusps": None, "ok": False, "error": str(exc)}
        if name == "porphyry":
            out["ascendant"] = ascmc[0]
            out["mc"] = ascmc[1]
            out["armc"] = ascmc[2]
    return out


def _rise_set(jd_ut: float, lat: float, lon: float, alt: float) -> dict[str, float | None]:
    """Next sunrise and sunset after (jd_ut - 0.5) under two definitions."""
    geopos = (lon, lat, alt)
    start = jd_ut - 0.5
    results: dict[str, float | None] = {}
    definitions = {
        "hindu": swe.BIT_HINDU_RISING,
        "upper_limb_refraction": 0,
        "disc_centre_refraction": swe.BIT_DISC_CENTER,
    }
    for label, bits in definitions.items():
        for event, rsmi in (("rise", swe.CALC_RISE), ("set", swe.CALC_SET)):
            res, tret = swe.rise_trans(start, swe.SUN, rsmi | bits, geopos, 1013.25, 15.0)
            results[f"{label}_{event}"] = tret[0] if res == 0 else None
    return results


def main() -> None:
    swe.set_ephe_path(str(EPHE))
    rng = random.Random(SEED)
    cases_out = []
    for case_id, jd_ut, lat, lon, alt in _case_times(rng):
        delta_t_days = swe.deltat(jd_ut)
        jd_tt = jd_ut + delta_t_days
        mean_ayan, true_ayan = _ayanamsas(jd_tt)
        swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
        nut = swe.calc(jd_tt, swe.ECL_NUT, 0)[0]
        cases_out.append(
            {
                "id": case_id,
                "jd_ut": jd_ut,
                "jd_tt": jd_tt,
                "delta_t_s": delta_t_days * 86400.0,
                "lat": lat,
                "lon": lon,
                "alt_m": alt,
                "true_obliquity": nut[0],
                "mean_obliquity": nut[1],
                "nutation_longitude": nut[2],
                "nutation_obliquity": nut[3],
                "positions_tropical": _positions(jd_tt),
                "ayanamsa_mean": mean_ayan,
                "ayanamsa_true": true_ayan,
                "houses": _houses(jd_ut, lat, lon),
                "sun_rise_set": _rise_set(jd_ut, lat, lon, alt),
            }
        )
    payload = {
        "generator": "oracle/generate_astro_fixtures.py",
        "reference": f"Swiss Ephemeris {swe.version} (pyswisseph), files sepl_18/semo_18",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "seed": SEED,
        "conventions": {
            "positions": "apparent geocentric, true ecliptic and equinox of date, TT input",
            "ayanamsa_mean": "get_ayanamsa_ex with SEFLG_NONUT",
            "ayanamsa_true": "get_ayanamsa_ex including nutation in longitude",
            "houses": "tropical cusps from houses_ex(jd_ut, lat, lon)",
            "rise_set": "next event after jd_ut - 0.5; 1013.25 hPa, 15 C",
        },
        "cases": cases_out,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"wrote {len(cases_out)} cases to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
