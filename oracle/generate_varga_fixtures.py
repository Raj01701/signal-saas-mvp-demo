"""Generate divisional-chart (varga) reference tables with PyJHora (development only).

For every supported division and method, records the resulting sign for each part
of each sign, sampled at the middle of the part, plus a set of random longitudes
with their divisional longitudes. Runs in the isolated oracle venv; only numbers are
written, to ``engine/tests/fixtures/vargas_pyjhora.json``.

    oracle/.venv/bin/python oracle/generate_varga_fixtures.py
"""

from __future__ import annotations

import json
import random
from datetime import UTC, datetime
from pathlib import Path

from jhora.horoscope.chart import charts

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "engine" / "tests" / "fixtures" / "vargas_pyjhora.json"

# (division, method) pairs; method numbers are PyJHora's. Names describe the scheme.
METHODS: dict[int, dict[int, str]] = {
    2: {
        2: "parashara",
        1: "parivritti_even_reverse",
        4: "parivritti_cyclic",
        6: "parivritti_alternate",
    },
    3: {1: "parashara", 2: "parivritti_cyclic", 3: "parivritti_alternate", 4: "jagannatha"},
    4: {
        1: "parashara",
        2: "parivritti_cyclic",
        3: "parivritti_even_reverse",
        4: "parivritti_alternate",
    },
    5: {
        1: "parashara",
        2: "parivritti_cyclic",
        3: "parivritti_even_reverse",
        4: "parivritti_alternate",
    },
    6: {
        1: "parashara",
        2: "parivritti_cyclic",
        3: "parivritti_even_reverse",
        4: "parivritti_alternate",
    },
    7: {
        1: "parashara",
        2: "parashara_even_backward",
        3: "parashara_even_reverse_end_7th",
        4: "parivritti_cyclic",
        5: "parivritti_even_reverse",
        6: "parivritti_alternate",
    },
    8: {
        1: "parashara",
        2: "parivritti_cyclic",
        3: "parivritti_even_reverse",
        4: "parivritti_alternate",
    },
    9: {
        1: "parashara",
        2: "parashara_even_reverse",
        5: "parivritti_cyclic",
        6: "parivritti_alternate",
    },
    10: {
        1: "parashara",
        2: "parashara_even_backward",
        3: "parashara_even_reverse_9th_backward",
        4: "parivritti_cyclic",
        5: "parivritti_even_reverse",
        6: "parivritti_alternate",
    },
    11: {
        1: "parashara",
        2: "raman_anti_zodiacal",
        3: "parivritti_cyclic",
        4: "parivritti_even_reverse",
        5: "parivritti_alternate",
    },
    12: {
        1: "parashara",
        2: "parashara_even_reverse",
        3: "parivritti_cyclic",
        4: "parivritti_even_reverse",
        5: "parivritti_alternate",
    },
    16: {
        1: "parashara",
        2: "parashara_even_reverse",
        3: "parivritti_cyclic",
        4: "parivritti_alternate",
    },
    20: {
        1: "parashara",
        2: "parashara_even_reverse",
        3: "parivritti_cyclic",
        4: "parivritti_alternate",
    },
    24: {1: "parashara", 2: "parashara_even_reverse", 3: "parashara_double_reverse"},
    27: {1: "parashara", 2: "parashara_even_reverse", 3: "parivritti_alternate"},
    40: {
        1: "parashara",
        2: "parivritti_cyclic",
        3: "parivritti_even_reverse",
        4: "parivritti_alternate",
    },
    45: {
        1: "parashara",
        2: "parivritti_cyclic",
        3: "parivritti_even_reverse",
        4: "parivritti_alternate",
    },
    60: {
        1: "parashara",
        2: "parashara_from_aries",
        3: "parashara_even_reverse_from_aries",
        4: "parashara_even_reverse_from_sign",
    },
    81: {1: "parashara", 2: "parivritti_even_reverse", 3: "parivritti_alternate"},
    108: {
        1: "parashara",
        2: "parivritti_cyclic",
        3: "parivritti_even_reverse",
        4: "parivritti_alternate",
    },
    144: {
        1: "parashara",
        2: "parivritti_cyclic",
        3: "parivritti_even_reverse",
        4: "parivritti_alternate",
    },
}

# Trimsamsa (D30) has unequal parts; sample every 0.25 degree and near the boundaries.
D30_SAMPLES = [i * 0.25 + 0.125 for i in range(120)] + [
    4.999,
    5.001,
    7.999,
    8.001,
    9.999,
    10.001,
    11.999,
    12.001,
    17.999,
    18.001,
    19.999,
    20.001,
    24.999,
    25.001,
]


def _signs(division: int, method: int, positions: list[list[object]]) -> list[int]:
    result = charts.divisional_positions_from_rasi_positions(positions, division, method)
    return [int(sign) for _, (sign, _) in result]


def main() -> None:
    tables: dict[str, dict[str, list[list[int]]]] = {}
    for division, methods in METHODS.items():
        width = 30.0 / division
        positions = [
            [s * division + p, (s, (p + 0.5) * width)] for s in range(12) for p in range(division)
        ]
        tables[str(division)] = {}
        for method, name in methods.items():
            flat = _signs(division, method, positions)
            tables[str(division)][name] = [
                flat[s * division : (s + 1) * division] for s in range(12)
            ]

    d30_positions = [
        [i, (s, x)] for i, (s, x) in enumerate((s, x) for s in range(12) for x in D30_SAMPLES)
    ]
    d30 = {}
    for method, name in {1: "parashara", 2: "parivritti_cyclic"}.items():
        d30[name] = _signs(30, method, d30_positions)

    rng = random.Random(20260930)
    samples = [[i, (rng.randrange(12), rng.uniform(0.0, 30.0))] for i in range(300)]
    longitudes = {}
    for division in [2, 3, 7, 9, 10, 12, 16, 20, 24, 27, 30, 40, 45, 60]:
        result = charts.divisional_positions_from_rasi_positions(samples, division, 1)
        longitudes[str(division)] = [[int(sign), float(lon)] for _, (sign, lon) in result]

    payload = {
        "generator": "oracle/generate_varga_fixtures.py",
        "reference": "PyJHora 4.8.7 charts.divisional_positions_from_rasi_positions",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "tables": tables,
        "d30_samples": D30_SAMPLES,
        "d30": d30,
        "random_inputs": [[int(s), float(x)] for _, (s, x) in samples],
        "random_outputs_method1": longitudes,
    }
    OUT.write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
