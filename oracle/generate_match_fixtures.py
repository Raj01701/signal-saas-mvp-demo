"""Generate marriage-matching references with PyJHora (development only).

For every pair of nakshatra padas (108 x 108, groom first), PyJHora's North Indian
Ashtakoota gives the eight koota scores (Vashya with its AstroYogi table, the one
the engine's default profile uses), and its Mahendra, Vedha, Rajju and South
Indian Vasya checks. Only numbers are written, to
``engine/tests/fixtures/match_pyjhora.json``.

    oracle/.venv/bin/python oracle/generate_match_fixtures.py
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from jhora.horoscope.match.compatibility import Ashtakoota

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "engine" / "tests" / "fixtures" / "match_pyjhora.json"
COLUMNS = [
    "groom_nakshatra", "groom_pada", "bride_nakshatra", "bride_pada", "varna", "vashya",
    "tara", "yoni", "graha_maitri", "gana", "bhakoot", "nadi", "mahendra", "vedha",
    "rajju", "vasya_south",
]  # fmt: skip


def main() -> None:
    rows = []
    padas = [(n, p) for n in range(1, 28) for p in range(1, 5)]
    for gn, gp in padas:
        for bn, bp in padas:
            north = Ashtakoota(gn, gp, bn, bp, method="North")
            rows.append(
                [
                    gn - 1, gp, bn - 1, bp,
                    north.varna_porutham()[0],
                    north.vasiya_porutham(use_astroyogi_method=True)[0],
                    north.tara_porutham()[0],
                    north.yoni_porutham()[0],
                    north.raasi_adhipathi_porutham()[0],
                    north.gana_porutham()[0],
                    north.raasi_porutham()[0],
                    north.naadi_porutham()[0],
                    int(north.mahendra_porutham()),
                    int(north.vedha_porutham()),
                    int(north.rajju_porutham()),
                    int(Ashtakoota(gn, gp, bn, bp, method="South").vasiya_porutham()),
                ]
            )  # fmt: skip
    payload = {
        "generator": "oracle/generate_match_fixtures.py",
        "reference": "PyJHora (jhora.horoscope.match.compatibility)",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "columns": COLUMNS,
        "rows": rows,
    }
    OUT.write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"wrote {len(rows)} pairs to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
