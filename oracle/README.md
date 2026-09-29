# Oracle harness (development only, never shipped)

Generates **numeric reference fixtures** by running independent, mature implementations:

- **Swiss Ephemeris** via `pyswisseph` (AGPL-3.0)
- **PyJHora** (AGPL-3.0), whose ~6,800 tests were checked against Jagannatha Hora 8.0

These tools are AGPL, so they live in their own virtual environment (`oracle/.venv`),
are never listed as product dependencies, and are never imported by `engine/` or `api/`
(`engine/tests/test_license_guard.py` enforces this). Only the generated numbers
(`engine/tests/fixtures/*.json`) are committed.

Swiss Ephemeris data files are fetched from the official GitHub repository
(`aloistr/swisseph`, `ephe/`), because astro.com is not reachable from the build
environment.

## Usage

```bash
oracle/setup.sh                                          # isolated venv + data files
oracle/.venv/bin/python oracle/generate_astro_fixtures.py
uv run python scripts/accuracy_report.py                 # refresh docs/ACCURACY.md
```

The report script runs in the product environment; it only reads the fixture numbers.
