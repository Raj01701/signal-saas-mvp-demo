"""Write the API's OpenAPI schema for the web app's generated types.

    uv run python scripts/export_openapi.py          # write web/src/lib/api/openapi.json
    uv run python scripts/export_openapi.py --check  # fail if it is out of date

Then ``pnpm -C web api:types`` regenerates ``web/src/lib/api/schema.d.ts``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from jyotish_api.main import create_app

OUT = Path(__file__).resolve().parent.parent / "web" / "src" / "lib" / "api" / "openapi.json"


def main() -> int:
    text = json.dumps(create_app().openapi(), indent=2, sort_keys=True) + "\n"
    if "--check" in sys.argv:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            print(f"{OUT} is out of date: run scripts/export_openapi.py", file=sys.stderr)
            return 1
        return 0
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
