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
| `rules/` | Chart facts (from a chart or a compact test spec); the rule language (safe parser and evaluator with evidence); the rule schema; the catalogue loader, which checks citations against `knowledge/sources.yaml` and orders rules that refer to each other; `compute_yogas(chart)` and `compute_readings(chart)` (the result of each placement) |
| `predict/` | Life domains with their houses, karakas, divisional charts and ages (`domains.py`); each domain's natal promise from its lords' dignity, placement and Shadbala, Ashtakavarga bindus, occupants, aspects, karakas, divisional-chart dignity and the knowledge base's yogas and readings (`promise.py`); the monthly timeline, where the running Vimshottari lords' links to the domain (period) and Jupiter's and Saturn's transits (trigger) multiply the promise, Yogini dasha agreement raises confidence, and windows carry their evidence and matching dasha and transit rules (`timeline.py`, about 0.4 s for 60 years) |
| `rectify/` | Life-event kinds and the houses, karakas and divisional chart that signify each (`events.py`); the candidate scan, where only the lagna (the sidereal angle advances at the sidereal rate), the Moon (from its speed) and so the dashas change, events scored through the same links as the prediction timeline down to the sookshma, optional Kunda, Pranapada and navamsa-gender priors, and plateau-aware ranking of distinct candidates (`search.py`); synthetic events drawn from the engine's own rules for acceptance tests (`synthetic.py`) |
| `sensitivity.py` | How many minutes each time-sensitive factor (D1, D9, D10 and D60 lagnas, the Moon's nakshatra pada) holds before and after the birth time, flagged when it would change within the time's uncertainty |
| `models.py` | Public input and output models (pydantic, JSON-serialisable) |
| `settings.py` | Calculation settings, presets and the settings fingerprint |
| `chart.py` | `compute_chart(BirthInput, Settings) -> ChartResult`: about 80 ms per chart |

## API (`api/`)

FastAPI app built by `create_app(settings)` (`jyotish_api/main.py`); configuration comes from `JYOTISH_API_*` environment variables (`config.py`).

- Stateless calculation routes under `/v1` (`routers/compute.py`): place search, chart, yogas, natal readings, period readings (`/charts/period`), predictions (`/charts/predictions`), birth-time rectification (`/rectify`), strengths, any dasha system, transits, annual charts, KP (natal and horary), panchanga and matchmaking. Request bodies take a full `settings` object or a `preset`.
- Charts are cached in memory, keyed by a hash of birth data and settings (`charts.py`); uncached chart p95 is about 230 ms.
- Engine `ValueError`s (dates outside the ephemeris, polar days, unknown options) become HTTP 422; rate limiting per client address uses slowapi.
- Account routes (`routers/account.py`, sign-in required): profile and research consent, saved people with birth data, life events for rectification and backtesting, `GET /v1/me/export` and `DELETE /v1/me` (everything saved is deleted). A minor's data needs the guardian's consent (DPDP Act).
- Supabase access tokens are verified locally with the project's HS256 secret or its JWKS (`auth.py`); the first request from a user creates their account.
- SQLAlchemy 2 models (`db.py`) with Alembic migrations (`api/migrations`, run `alembic upgrade head` from `api/`); SQLite for development and tests, Postgres in production through the pg8000 driver (the LGPL psycopg drivers are excluded by the licence guard). A test fails if models and migrations drift; a Postgres round trip runs when `JYOTISH_API_TEST_POSTGRES_URL` is set.
- `scripts/export_openapi.py` writes `web/src/lib/api/openapi.json`, and `pnpm -C web api:types` generates `schema.d.ts` from it; CI fails when either is stale.

## Web (`web/`)

Next.js (App Router) with Tailwind. The pages are client components that call the API directly with `openapi-fetch`, typed by the generated `src/lib/api/schema.d.ts`; `NEXT_PUBLIC_API_URL` points them at the API.

- `/workbench`: chart, dashas, yogas, natal readings, the prediction timeline (with what the running dasha and transits say now), strengths, transits, KP and birth-time sensitivity for one birth.
- `/panchanga`: the Hindu day for a date and place, with times shown in the place's local time.
- `/match`: horoscope matching of two births.
- `/rectify`: birth-time rectification from dated life events, with a scan of the window and the ranked candidates.
- Shared form pieces: `PlaceField` (gazetteer search with a coordinates fallback) and `BirthFields` (date, time and place), both controlled; pure formatting helpers live in `lib/format.ts`.

- Chart drawings are SVG (`components/ChartDiagram.tsx`); their geometry for the North, South and East Indian styles is pure and unit-tested (`lib/chart-layout.ts`).
- End-to-end tests (`web/e2e`, Playwright) start the API and a production build, then check every page on desktop and mobile viewports, including axe WCAG A/AA rules and horizontal overflow against the configured viewport width (a mobile browser would otherwise widen its layout viewport and hide the overflow). `PW_CHROMIUM` selects an installed Chromium.

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
location). It holds 312 yogas and doshas (`knowledge/yogas/`, about 4 ms per chart) and
375 natal readings (`knowledge/natal/`, about 2.5 ms): each house lord in each house,
each graha in each house and sign, the Moon's nakshatra and the rising sign, written by
`scripts/generate_readings.py`. [`knowledge/README.md`](../knowledge/README.md) is the
authoring guide.

## Oracle harness (`oracle/`)

This is a separate virtual environment containing pyswisseph and PyJHora (both AGPL). It is never installed with, or imported by, the product. It generates numeric fixtures, `engine/tests/fixtures/*.json`, which the golden tests compare against.
`scripts/accuracy_report.py` turns those comparisons into `docs/ACCURACY.md`.
