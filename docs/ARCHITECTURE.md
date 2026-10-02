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
| `match/` | Ashtakoota (36 points) with Nadi, Bhakoot and Gana doshas and their exceptions; Raman's ten South Indian kutas with his reliefs; Kuja dosha of both charts from the knowledge base; koota tables kept as cited, named profiles because sources differ (`tables.py`); papasamya, lagna lords, navamsa lagnas, each Moon in the other's chart and dasha sandhi (`compatibility.py`); `compute_match(groom, bride)` |
| `rules/` | Chart facts (from a chart or a compact test spec); the rule language (safe parser and evaluator with evidence); the rule schema; the catalogue loader, which checks citations against `knowledge/sources.yaml` and orders rules that refer to each other; `compute_yogas(chart)` and `compute_readings(chart)` (the result of each placement) |
| `predict/` | Life domains with their houses, karakas, divisional charts and ages (`domains.py`); each domain's natal promise from its lords' dignity, placement and Shadbala, Ashtakavarga bindus, occupants, aspects, karakas, divisional-chart dignity and the knowledge base's yogas and readings (`promise.py`); the monthly timeline, where the running Vimshottari lords' links to the domain (period) and Jupiter's and Saturn's transits (trigger) multiply the promise, Yogini dasha agreement raises confidence, and windows carry their evidence and matching dasha and transit rules (`timeline.py`, about 0.6 s for 60 years); further techniques, each switchable for the Accuracy Lab: the dasha lords' links in the domain's divisional chart, Jaimini Chara dasha and KP house groups as further agreeing systems, Ashtakavarga-weighted transits and Saturn with Jupiter on the house lord (`techniques.py`; on 20 well-documented charts none beat chance, see `ACCURACY_REAL.md`); the life reading, told the way an astrologer talks (`story.py`, `/v1/charts/life-reading`): the chart at a glance; who you are (rising sign, Moon sign, birth star, the chart ruler, strong planets and well-known yogas); your life so far as chapters, one per mahadasha, each with the stretches that stood out, and the main past stretch per area to check against real events; where you stand now (the running periods, Sade Sati, Saturn and Jupiter, the coming months, traditional remedies); the years ahead one by one; life areas, among them career fields scored against the tenth house, its ruler, planets in and aspecting it, the source of earnings (the tenth lord's navamsa lord) and the amatyakaraka, foreign travel and settlement from the twelfth-house links and Rahu, and health as traditional tendencies with a doctor's note; marriage and spouse (the partner described, where you may meet, love or arranged, married life and timing, for readers 18 and over), with timing read for the life the person states (`marital`: married, with the wedding year checked against the chart's windows and later windows read as married life; not married, with past windows as times relationships were in focus and later ones as openings; or unknown, allowing for either); Manglik, Sade Sati and favourable things; and remedies chosen for the chart (the running period, weak planets, Sade Sati and doshas, the weakest area, gemstones and daily practice) (`topics.py`, `lore.py`). Active stretches (windows) are found once per reading, over the whole life, so they do not change with the date of the reading: a window reaches the person's own top fifth of months for the area, lasts while the months stay in the top 30%, joins runs inside one Vimshottari sub-period, and needs at least two months; its tenor is judged against the person's usual tenor. A window is strong when it is at least 80% as active as the area's strongest window at the ages the area is mainly read. Every section names the same windows, and `LifeReadingOut.windows` lists them with their dates, ages, tenor, strength and sub-periods for the timeline and the chat: the life chapters, the checks, the coming months, the years ahead, the area cards (the next strong window and the strongest ahead), the marriage section (the first two strong windows behind, the next and the strongest ahead) and the wedding check. A wedding or a birth is told only for a strong window; past marriage windows are told as the chart's times for marriage, not as weddings, unless the person gave the wedding date; children are never told as past events for someone not known to be married. Manglik names where Mars is counted from (rising sign, Moon, Venus), since matching apps differ. Everything is read for the age it falls in (`words.MOMENTS`): childhood is about home, school and family, marriage is read from 21 (settling down from 24, two years earlier for women), children from 25 and after the marriage stretch; a reader under 18 gets nothing about marriage, children or romance. The past is dated in years and told in the past tense, the future to the month; phrasing varies steadily per chart (`voice.py`); all wording is our own (`words.py`), with no jargon, nothing on death or illness, and a technical basis kept for astrologers |
| `ask/` | Lookups for questions about one chart (`lookup.py`, `ChartLookup`): a planet (sign, house, dignity, the houses it rules and aspects, conjunctions, divisional-chart signs, chara karaka, Shadbala), a house (sign, lord and its placement, occupants, aspects, Ashtakavarga bindus, Bhava Bala), the periods and every transit on a date, the periods or the slow transits across a range (each stay from its real ingress to its egress, with Sade Sati and the other Saturn notes), a life area's promise and windows across the whole life, and one calendar year (annual chart, periods, transits, windows). Each result prints itself as one line of evidence. Names of planets and areas are recognised in English, Hinglish and Devanagari. |
| `rectify/` | Life-event kinds and the houses, karakas and divisional chart that signify each (`events.py`); the candidate scan, where only the lagna (the sidereal angle advances at the sidereal rate), the Moon (from its speed) and so the dashas change, events scored through the same links as the prediction timeline down to the sookshma, optional Kunda, Pranapada and navamsa-gender priors, and plateau-aware ranking of distinct candidates (`search.py`); synthetic events drawn from the engine's own rules for acceptance tests (`synthetic.py`) |
| `lab/` | The Accuracy Lab (`backtest.py`): each case's events scored by the percentile of their month in the domain's timeline and by window hits, for the recorded birth and for shuffled-time and swapped-event controls; lift, a permutation p-value and calibration by confidence label. `scripts/accuracy_lab.py` runs it on recorded cases (JSON lines; `scripts/export_research_cases.py` exports research-consented adults without names) or on synthetic ones, writing `docs/ACCURACY_LAB.md` |
| `sensitivity.py` | How many minutes each time-sensitive factor (D1, D9, D10 and D60 lagnas, the Moon's nakshatra pada) holds before and after the birth time, flagged when it would change within the time's uncertainty |
| `models.py` | Public input and output models (pydantic, JSON-serialisable) |
| `settings.py` | Calculation settings, presets and the settings fingerprint |
| `chart.py` | `compute_chart(BirthInput, Settings) -> ChartResult`: about 80 ms per chart |

## API (`api/`)

FastAPI app built by `create_app(settings)` (`jyotish_api/main.py`); configuration comes from `JYOTISH_API_*` environment variables (`config.py`).

- Stateless calculation routes under `/v1` (`routers/compute.py`): place search, chart, yogas, natal readings, period readings (`/charts/period`), predictions (`/charts/predictions`), birth-time rectification (`/rectify`), strengths, any dasha system, transits, annual charts, KP (natal and horary), panchanga and matchmaking. Request bodies take a full `settings` object or a `preset`.
- Charts are cached in memory, keyed by a hash of birth data and settings (`charts.py`); uncached chart p95 is about 230 ms.
- Engine `ValueError`s (dates outside the ephemeris, polar days, unknown options) become HTTP 422. Rate limiting uses slowapi's ASGI middleware per client address; behind proxies the address is read from the entries the trusted proxies appended to `X-Forwarded-For` (`ratelimit.py`, `JYOTISH_API_FORWARDED_HOPS`). The report and chat routes have their own, stricter quota.
- `observability.py`, a pure ASGI middleware: request IDs (`X-Request-ID`), one JSON access line per request (route templates, never bodies or client addresses), Prometheus metrics at `/metrics` (optionally behind a bearer token), security headers, and a body-size limit that also counts streamed bodies.
- Account routes (`routers/account.py`, sign-in required): profile and research consent, saved people with birth data, life events for rectification and backtesting, `GET /v1/me/export` and `DELETE /v1/me` (everything saved is deleted). A minor's data needs the guardian's consent (DPDP Act).
- Supabase access tokens are verified locally with the project's HS256 secret or its JWKS (`auth.py`); the first request from a user creates their account.
- SQLAlchemy 2 models (`db.py`) with Alembic migrations (`api/migrations`, run `alembic upgrade head` from `api/`); SQLite for development and tests, Postgres in production through the pg8000 driver (the LGPL psycopg drivers are excluded by the licence guard), with `JYOTISH_API_DATABASE_TLS=verify-full` checking the server's certificate. Migration 0002 turns on row-level security, so Supabase's REST API exposes nothing. A test fails if models and migrations drift; a Postgres round trip runs when `JYOTISH_API_TEST_POSTGRES_URL` is set.
- Narratives (`narrative/`, `routers/narrative.py`): `build_bundle` gathers the engine's evidence for a chart, each item with a stable ID (`rule:…`, `promise:career`, `window:career:2027-03`, `now:dasha`, …). A narrator turns the bundle into a report: the offline `TemplateNarrator` by default, or `ClaudeNarrator` when `JYOTISH_API_ANTHROPIC_API_KEY` is set (`JYOTISH_API_NARRATIVE_PROVIDER` chooses). Claude is called through the official Anthropic SDK, with server-side refusal fallbacks; the report arrives as structured output in the `Report` schema (the current models do not accept forced tool calls), with the system prompt cached. Before anything is returned, `report.check` rejects evidence IDs outside the bundle and banned claims (death timing, medical, legal or financial directives, guarantees, fear-based remedies); a failed report is retried once. Chat takes any question in the person's own words (`/v1/charts/chat`, with the conversation so far, an optional first name and the reply language). Claude may call seven strict lookup tools over `ChartLookup` (`narrative/tools.py`: `planet`, `house`, `period_at`, `periods`, `transits`, `life_area`, `year`), each returning the engine's result with an evidence id, and then answers as JSON (`answer`, `evidence_ids`). Cited lookup ids it did not call are run to verify them; an answer citing unknown evidence or making a banned claim goes back to the model with the reason, for up to six rounds. Without a key, `answer_offline` lists the engine's facts on the years ("2028", "next year", "agle saal"), houses ("7th house", "सातवाँ भाव"), planets and life areas the question names, in English, and declines death, lifespan and accident timing. `scripts/narrative_eval.py` measures both on 50 bundles.
- Push reminders (`push.py`, `routers/push.py`): a browser subscribes with the operator's VAPID key (`GET /v1/push/key`) and saves the reminders it computed (`PUT /v1/push/subscription`; no account or birth data). `python -m jyotish_api.push send`, run on a schedule, encrypts each due reminder for its browser (RFC 8291) and posts it, with a VAPID token, only to the browsers' push services; sent reminders are deleted and dead or idle subscriptions forgotten.
- `scripts/export_openapi.py` writes `web/src/lib/api/openapi.json`, and `pnpm -C web api:types` generates `schema.d.ts` from it; CI fails when either is stale.

- Deployment: `api/Dockerfile` builds the image from the repository root (dependencies with uv, DE440 downloaded and checked against a pinned SHA-256, a non-root user, private docs); [RUNBOOK.md](RUNBOOK.md) covers configuration, migrations, monitoring, data requests and incidents, and [SECURITY.md](SECURITY.md) the security review.

## Web (`web/`)

Next.js (App Router) with Tailwind. The pages are client components that call the API directly with `openapi-fetch`, typed by the generated `src/lib/api/schema.d.ts`; `NEXT_PUBLIC_API_URL` points them at the API. It may instead be a path such as `/api`: the web server then forwards those requests to `API_PROXY_TARGET`, so one public port serves both. The codespace setup in `.devcontainer/` runs this way.

- `/workbench`: chart, dashas, yogas, natal readings, a cited plain-language report with questions answered from the evidence, the prediction timeline (with what the running dasha and transits say now), strengths, transits, KP and birth-time sensitivity for one birth.
- `/panchanga`: the Hindu day for a date and place, with times shown in the place's local time.
- `/match`: horoscope matching of two births.
- `/rectify`: birth-time rectification from dated life events, with a scan of the window and the ranked candidates.
- `/my`: the consumer app. Onboarding records the birth details and how certain the time is (source and ± minutes, sent as `time_source` and `uncertainty_minutes`); the dashboard shows today, this month and the year ahead from `/v1/panchanga`, `/v1/charts/period` and `/v1/charts/predictions`, with reminders and a calendar export. The profile stays in the browser (`lib/profile.ts`). With push on, the reminders can also come as notifications (`lib/push.ts`, the service worker `public/sw.js`, served with its own strict policy).
- Languages: English and Hindi from typed dictionaries (`lib/dictionaries.ts`, `lib/i18n.ts`; the Hindi dictionary must have the English one's shape, which a unit test checks) and localized names (`lib/names.ts`). The choice is remembered per device; the server renders English and the page switches after hydration.
- `/privacy` and `/terms` (drafts for legal review), linked with the interpretive disclaimer from the footer of every page. `next.config.ts` sends a content security policy (scripts, styles and fonts from the site, API calls only to `NEXT_PUBLIC_API_URL`), HSTS and the other security headers.
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
