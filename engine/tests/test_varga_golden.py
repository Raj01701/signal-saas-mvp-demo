"""Golden tests: divisional charts versus PyJHora reference tables."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest

from jyotish_engine.core.varga import VargaMethod, varga_longitude, varga_sign_index

FIXTURE = Path(__file__).parent / "fixtures" / "vargas_pyjhora.json"

pytestmark = pytest.mark.golden

# Reference method names that map onto engine methods.
SUPPORTED = {
    "parashara": VargaMethod.PARASHARA,
    "parashara_even_reverse": VargaMethod.PARASHARA_EVEN_REVERSE,
    "parivritti_cyclic": VargaMethod.PARIVRITTI_CYCLIC,
    "parivritti_even_reverse": VargaMethod.PARIVRITTI_EVEN_REVERSE,
    "parivritti_alternate": VargaMethod.PARIVRITTI_ALTERNATE,
    "jagannatha": VargaMethod.JAGANNATHA,
    "raman_anti_zodiacal": VargaMethod.RAMAN,
    "parashara_double_reverse": VargaMethod.SIDDHAMSA_FROM_LEO,
}


@lru_cache(maxsize=1)
def data() -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return loaded


def _table_cases() -> list[tuple[int, str]]:
    return [
        (int(division), name)
        for division, methods in data()["tables"].items()
        for name in methods
        if name in SUPPORTED
    ]


@pytest.mark.parametrize(("division", "reference_method"), _table_cases())
def test_varga_tables(division: int, reference_method: str) -> None:
    table = data()["tables"][str(division)][reference_method]
    method = SUPPORTED[reference_method]
    width = 30.0 / division
    for sign in range(12):
        ours = [
            varga_sign_index(sign, (p + 0.5) * width, division, method) for p in range(division)
        ]
        assert ours == table[sign], f"D{division} {reference_method} sign {sign}"


@pytest.mark.parametrize(
    ("reference_method", "method"),
    [("parashara", VargaMethod.PARASHARA), ("parivritti_cyclic", VargaMethod.PARIVRITTI_CYCLIC)],
)
def test_trimsamsa(reference_method: str, method: VargaMethod) -> None:
    samples = data()["d30_samples"]
    expected = data()["d30"][reference_method]
    ours = [varga_sign_index(s, x, 30, method) for s in range(12) for x in samples]
    assert ours == expected


def test_divisional_longitudes() -> None:
    reference_method_1 = {
        # PyJHora's method 1 is Parashara except for the hora (parivritti even-reverse).
        2: VargaMethod.PARIVRITTI_EVEN_REVERSE,
    }
    inputs = data()["random_inputs"]
    for division_text, outputs in data()["random_outputs_method1"].items():
        division = int(division_text)
        method = reference_method_1.get(division, VargaMethod.PARASHARA)
        for (sign, degrees), (ref_sign, ref_long) in zip(inputs, outputs, strict=True):
            result = varga_longitude(30.0 * sign + degrees, division, method)
            assert int(result // 30.0) == ref_sign, (division, sign, degrees)
            assert result % 30.0 == pytest.approx(ref_long, abs=1e-9)
