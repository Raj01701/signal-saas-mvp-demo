# Architecture

```
Next.js web (pro workbench + consumer app) ──typed client (OpenAPI)──► FastAPI service (api/)
                                                                          │
      Postgres + Auth (Supabase) ◄── SQLAlchemy / Alembic ────────────────┤
                                                                          ▼
                  jyotish_engine (engine/) ◄── knowledge/ YAML rule base
                                                                          │
                  LLM narrative layer (evidence in, cited prose out)
```

## Principles

1. **The engine is pure and deterministic.**
   - The same birth data, settings and engine version always give identical output.
   - The only I/O is reading the ephemeris kernel.
2. **Layers are tested in isolation.**
   - Astronomy is compared against the oracles on its own.
   - Jyotish logic is tested by feeding it identical longitudes. This matters because a 1″ difference in the Moon alone moves dasha dates by hours.
3. **Every result is reproducible.** Results carry `engine_version` and a hash of the settings.
4. **Only permissively licensed dependencies ship.**
   - CI runs `scripts/check_licenses.py`.
   - `engine/tests/test_license_guard.py` blocks AGPL imports in product code.
5. **The LLM never calculates.** It turns engine evidence (rule IDs with citations) into prose, and the server validates every evidence ID it cites.

## Engine modules (`engine/jyotish_engine/`)

| Module | Responsibility |
|---|---|
| `astro/` | Time scales and ΔT; ephemeris loading (DE440 → DE421 fallback); apparent positions and speeds; mean and true nodes; ayanamsa family; house systems; rise and set; fixed stars |
| `place/` | Geocoding (GeoNames); timezone from coordinates; historical time overrides (`overrides/*.yaml`); local time → UTC resolution with ambiguity flags |
| `core/` | Signs, nakshatras, padas, KP subdivisions; divisional charts and their variants; dignity; planetary relationships; avasthas; combustion; planetary war |
| `special/` | Upagrahas, special lagnas, arudha padas, chara karakas, sahams |
| `strength/` | Shadbala, Bhava Bala, Vimshopaka, Ashtakavarga |
| `dasha/` | A generic period tree; Vimshottari and the other nakshatra dashas; Jaimini sign dashas |
| `transit/` | Ingress and station search; Sade Sati; double transit; Ashtakavarga transit scoring |
| `annual/` | Varshaphal (Tajika), Mudda and Patyayini dashas, Tithi Pravesha |
| `kp/` | KP significators and ruling planets |
| `panchanga/` | Panchanga elements, their end times, muhurta periods, calendar |
| `match/` | Ashtakoota, Dashakoota, Manglik |
| `rules/` | Rule DSL parser and safe evaluator; converts a chart into facts |
| `predict/` | Promise × period × trigger timeline; convergence; confidence |
| `rectify/` | Candidate grid, event scoring, classical priors, sensitivity |
| `chart.py` | `compute_chart(BirthInput, Settings) -> ChartResult` |

## Ephemeris resolution

1. The environment variable `JYOTISH_EPHEMERIS` (an explicit path to a `.bsp` kernel).
2. `de440.bsp` in `JYOTISH_DATA_DIR` (default `data/ephemeris/`). The production image downloads it at build time and verifies its SHA-256.
3. The `de421.bsp` bundled by `skyfield-data` (1899-07-28 to 2053-10-08). This is the offline development fallback.

The loaded kernel name and date range are recorded in every result. Requests outside the kernel's range fail with a clear error; the engine never extrapolates.

## Oracle harness (`oracle/`)

This is a separate virtual environment containing pyswisseph and PyJHora (both AGPL). It is never installed with, or imported by, the product. It generates numeric fixtures, `engine/tests/fixtures/*.json`, which the golden tests compare against.
