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
| `astro/` | Time scales and ΔT; ephemeris loading (DE440 → DE421 fallback); apparent positions and speeds; mean and true nodes; ayanamsa family; house systems; rise and set of the Sun (two sunrise definitions) and the Moon (topocentric, with its semidiameter); fixed stars |
| `place/` | Geocoding (GeoNames); timezone from coordinates; historical time overrides (`overrides/*.yaml`); local time → UTC resolution with ambiguity flags |
| `core/` | Signs, nakshatras, padas, KP subdivisions; divisional charts and their variants; dignity; planetary relationships; avasthas; combustion; planetary war |
| `special/` | Upagrahas, special lagnas, arudha padas, chara karakas, sahams |
| `strength/` | Shadbala, Bhava Bala, Vimshopaka, Ashtakavarga |
| `dasha/` | A generic period tree; Vimshottari and the other nakshatra dashas with their applicability rules; dasha-year options; Chara, Narayana and Shoola sign dashas (Jaimini sign strength in `core/jaimini.py`); Kalachakra |
| `transit/` | Ingress, longitude-crossing and station search on vectorised sidereal positions (`astro/series.py`); Sade Sati; double transit; Ashtakavarga transit scoring |
| `annual/` | Varsha Pravesha and the annual chart, Muntha, office-bearers, Tajika aspects (ithasala, isarapha), pancha-vargiya bala and the lord of the year, the 36 sahams, Mudda and Patyayini dashas, Tithi Pravesha |
| `kp/` | Star, sub and sub-sub lords and the 249 horary divisions (`subdivisions.py`); Placidus bhava placement, four-level significators with Rahu and Ketu as agents of their sign lords, ruling planets, horary cusps solved for the moment the number's ascendant rises (`significators.py`); `compute_kp(chart)` and `compute_kp_horary(number, moment, place)` (`chart.py`) |
| `panchanga/` | Limb names and indices (`elements.py`); limb start and end times, all four limbs bisected together on shared Sun and Moon evaluations (`timing.py`); Rahu kalam, Yamaganda, Gulika, Abhijit, Brahma muhurta, durmuhurtas, horas and choghadiyas (`muhurta.py`); amanta and purnimanta months with adhika, nija and kshaya months, Kali, Shaka and Vikram years, samvatsara, ritu, ayana and the Tamil solar date, with new moons and sankrantis solved by Newton's method (`calendar.py`); `compute_panchanga(date, place)`, the Hindu day from sunrise to sunrise with its calendar date and kshaya or vriddhi tithis, in about 330 ms (`day.py`) |
| `match/` | Ashtakoota (36 points) with Nadi, Bhakoot and Gana doshas and their exceptions; Raman's ten South Indian kutas with his reliefs; Kuja dosha of both charts from the knowledge base; koota tables kept as cited, named profiles because sources differ (`tables.py`); `compute_match(groom, bride)` |
| `rules/` | Chart facts (from a chart or a compact test spec); the rule language (safe parser and evaluator with evidence); the rule schema; the catalogue loader, which checks citations against `knowledge/sources.yaml` and orders rules that refer to each other; `compute_yogas(chart)` |
| `predict/` | Promise × period × trigger timeline; convergence; confidence |
| `rectify/` | Candidate grid, event scoring, classical priors, sensitivity |
| `models.py` | Public input and output models (pydantic, JSON-serialisable) |
| `settings.py` | Calculation settings, presets and the settings fingerprint |
| `chart.py` | `compute_chart(BirthInput, Settings) -> ChartResult`: about 80 ms per chart |

## Ephemeris resolution

1. The environment variable `JYOTISH_EPHEMERIS` (an explicit path to a `.bsp` kernel).
2. `de440.bsp` in `JYOTISH_DATA_DIR` (default `data/ephemeris/`). The production image downloads it at build time and verifies its SHA-256.
3. The `de421.bsp` bundled by `skyfield-data` (1899-07-28 to 2053-10-08). This is the offline development fallback.

The loaded kernel name and date range are recorded in every result. Requests outside the kernel's range fail with a clear error; the engine never extrapolates.

## Time handling

Planet positions use TT. Sidereal time, and therefore the ascendant and cusps,
uses UT1. Civil birth times are resolved to UTC by `place/timezone.py`: the IANA
tz database, plus curated Indian rules (Bombay Time, Calcutta Time, local mean
time, war-time advisories). Every resolution returns the alternatives it rejected,
a confidence level and warnings, so ambiguous records are surfaced rather than
silently guessed.

## Knowledge base (`knowledge/`)

Rules are data: YAML files validated against `rules/schema.py`, each with citations
(text, edition, chapter or locator), provenance (classical, traditional or modern),
review status and its own positive, negative and cancelled test charts. The
catalogue is loaded once per process (`JYOTISH_KNOWLEDGE_DIR` overrides the
location) and evaluates all 312 current rules in about 4 ms per chart.
[`knowledge/README.md`](../knowledge/README.md) is the authoring guide.

## Oracle harness (`oracle/`)

This is a separate virtual environment containing pyswisseph and PyJHora (both AGPL). It is never installed with, or imported by, the product. It generates numeric fixtures, `engine/tests/fixtures/*.json`, which the golden tests compare against.
`scripts/accuracy_report.py` turns those comparisons into `docs/ACCURACY.md`.
