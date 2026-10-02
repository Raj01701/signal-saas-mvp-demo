"""Generate Tajika saham references from PyJHora (development only).

Sahams depend only on longitudes and on day or night, so random positions are used
directly (no ephemeris). For each case the script records PyJHora's 36 sahams and
the sign lords it chose, because PyJHora takes the stronger of Mars and Ketu for
Scorpio and of Saturn and Rahu for Aquarius, where Tajika uses the planet.

Only numbers are written, to ``engine/tests/fixtures/sahams_pyjhora.json``.

    oracle/.venv/bin/python oracle/generate_saham_fixtures.py
"""

from __future__ import annotations

import contextlib
import io
import json
import random
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jhora.horoscope.chart import house
from jhora.horoscope.transit import saham

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "engine" / "tests" / "fixtures" / "sahams_pyjhora.json"
SEED = 20261101
N_CASES = 300
NAMES = [
    "sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn", "rahu", "ketu",
]  # fmt: skip
#: Our saham name -> PyJHora function and whether it takes the night flag.
FUNCTIONS = {
    "punya": ("punya_saham", True),
    "vidya": ("vidya_saham", True),
    "yasas": ("yasas_saham", True),
    "mitra": ("mitra_saham", True),
    "mahatmya": ("mahatmaya_saham", True),
    "asha": ("asha_saham", True),
    "samartha": ("samartha_saham", True),
    "bhratri": ("bhratri_saham", False),
    "gaurava": ("gaurava_saham", True),
    "pitri": ("pithri_saham", True),
    "rajya": ("rajya_saham", True),
    "matri": ("maathri_saham", True),
    "putra": ("puthra_saham", True),
    "jeeva": ("jeeva_saham", True),
    "karma": ("karma_saham", True),
    "roga": ("roga_saham", True),
    "kali": ("kali_saham", True),
    "sastra": ("sastra_saham", True),
    "bandhu": ("bandhu_saham", True),
    "mrityu": ("mrithyu_saham", False),
    "paradesa": ("paradesa_saham", True),
    "artha": ("artha_saham", True),
    "paradara": ("paradara_saham", True),
    "vanik": ("vanika_saham", True),
    "karyasiddhi": ("karyasiddhi_saham", True),
    "vivaha": ("vivaha_saham", True),
    "santapa": ("santapa_saham", True),
    "sraddha": ("sraddha_saham", True),
    "preeti": ("preethi_saham", True),
    "jadya": ("jadya_saham", True),
    "vyapara": ("vyaapaara_saham", False),
    "satru": ("sathru_saham", True),
    "jalapatana": ("jalapatna_saham", True),
    "bandhana": ("bandhana_saham", True),
    "apamrityu": ("apamrithyu_saham", True),
    "labha": ("laabha_saham", True),
}


def _positions(lagna: float, planets: list[float]) -> list[Any]:
    """PyJHora's planet_positions: lagna first, then Sun ... Ketu as (sign, degrees)."""
    rows: list[Any] = [["L", (int(lagna // 30), lagna % 30)]]
    rows += [[i, (int(lon // 30), lon % 30)] for i, lon in enumerate(planets)]
    return rows


def main() -> None:
    rng = random.Random(SEED)
    cases = []
    for i in range(N_CASES):
        lagna = rng.uniform(0.0, 360.0)
        planets = [rng.uniform(0.0, 360.0) for _ in range(8)]
        planets.append((planets[7] + 180.0) % 360.0)  # Ketu opposite Rahu
        night = rng.random() < 0.5
        pp = _positions(lagna, planets)
        record: dict[str, Any] = {
            "id": f"s{i:03d}",
            "lagna": lagna,
            "planets": dict(zip(NAMES, planets, strict=True)),
            "night": night,
            "sahams": {},
        }
        with contextlib.redirect_stdout(io.StringIO()):
            for name, (function, takes_night) in FUNCTIONS.items():
                call = getattr(saham, function)
                value = call(pp, night) if takes_night else call(pp)
                record["sahams"][name] = float(value)
            record["lords"] = {
                "scorpio": NAMES[house.house_owner_from_planet_positions(pp, 7)],
                "aquarius": NAMES[house.house_owner_from_planet_positions(pp, 10)],
            }
        cases.append(record)
    payload = {
        "generator": "oracle/generate_saham_fixtures.py",
        "reference": "PyJHora 4.8.7 (horoscope/transit/saham.py)",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "seed": SEED,
        "cases": cases,
    }
    OUT.write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"wrote {len(cases)} cases to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
