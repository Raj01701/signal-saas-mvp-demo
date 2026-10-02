"""Product code must never import AGPL astrology libraries.

Swiss Ephemeris (pyswisseph) and PyJHora are only allowed inside the isolated
``oracle/`` harness, which generates numeric reference fixtures.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRODUCT_DIRS = [ROOT / "engine" / "jyotish_engine", ROOT / "api" / "jyotish_api"]
FORBIDDEN = re.compile(r"^\s*(import|from)\s+(swisseph|jhora|pyswisseph)\b", re.MULTILINE)


def test_product_code_does_not_import_agpl_libraries() -> None:
    offenders = [
        str(path.relative_to(ROOT))
        for directory in PRODUCT_DIRS
        for path in directory.rglob("*.py")
        if FORBIDDEN.search(path.read_text(encoding="utf-8"))
    ]
    assert offenders == [], f"AGPL imports found in product code: {offenders}"
