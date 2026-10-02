# Roadmap

Each milestone ends tested, committed and pushed. The status column is kept current.

| # | Milestone | Status |
|---|---|---|
| M0 | Foundation: monorepo, tooling, CI, licence guard, research, README | Done |
| M1 | Astronomy and place core, plus the oracle harness and golden fixtures | Done: see [ACCURACY.md](ACCURACY.md) |
| M2 | Jyotish basics: nakshatras, vargas, dignity, avasthas, special points | Done: see [ACCURACY.md](ACCURACY.md) |
| M3 | Timing: dashas, transits, Varshaphal and Tajika | Done: 11 nakshatra dashas with applicability and dasha-year options (including the true sidereal year); Chara (K.N. Rao) and Narayana sign dashas; Kalachakra; event search (ingresses, crossings, stations), Sade Sati and other Saturn transits, gochara with vedha, double transit; Varsha Pravesha and the annual chart, Muntha, office-bearers, Tajika aspects with ithasala and isarapha, Mudda and Patyayini dashas, Tithi Pravesha. See [ACCURACY.md](ACCURACY.md) |
| M4 | Strength and yogas: Shadbala, Ashtakavarga, rule DSL, 300+ yogas | Done: Ashtakavarga with reductions and pindas; Shadbala, Bhava Bala, Ishta and Kashta Phala, Vimshopaka; the rule language, schema and catalogue with 312 cited yogas and doshas, each with its own test charts (`knowledge/`); from M3, Tajika pancha-vargiya bala and the lord of the year, the 36 sahams, Ikkavala and Induvara, Ashtakavarga transit scoring (signs and kakshyas) and Shoola dasha. See [ACCURACY.md](ACCURACY.md). **Deferred until their definitions are checked against the texts:** the Tajika yogas between significators (Nakta, Yamaya, Kamboola and the others), and the Sthira, Brahma and Drig sign dashas, where sources and PyJHora's heuristics disagree |
| M5 | Panchanga, matchmaking, KP | Done: the day panchanga with tithi, nakshatra, yoga and karana end times, sunrise, sunset, moonrise and moonset, Rahu kalam, Yamaganda, Gulika, Abhijit, Brahma muhurta, durmuhurtas, horas and choghadiyas; every time within 0.11 s of Swiss Ephemeris on 560 dates; the lunisolar calendar (amanta and purnimanta months, adhika, nija and kshaya months, Kali, Shaka and Vikram years, the 60-year samvatsara, ritu, ayana, Tamil solar dates, kshaya and vriddhi tithis), checked on 704 dates against Swiss Ephemeris and PyJHora (see [ACCURACY.md](ACCURACY.md)). Matchmaking: Ashtakoota with dosha exceptions, the ten South Indian kutas, Kuja dosha comparison, checked on all 11,664 pada pairs against PyJHora. KP: cusp and planet lords, four-level significators, ruling planets, horary charts from the 249 numbers. **Deferred:** the North Indian (Jupiter-based) samvatsara, which drops a name about every 85 years and needs the expunction rule checked against almanacs; the day-one rules of the other regional solar calendars (Kerala, Bengal, Odisha); papasamya (malefic balance), until its weights are checked against a source |
| M6 | API and data layer: FastAPI, Postgres, auth, caching | Done: `/v1` calculation routes for every engine feature (chart cache, rate limiting, input errors as 422); accounts on Supabase tokens with saved people, life events, data export and deletion (SQLAlchemy and Alembic, SQLite or Postgres); OpenAPI export with generated TypeScript types checked in CI; uncached chart p95 about 230 ms |
| M7 | Pro workbench web app | Done: typed API client from the OpenAPI schema; `/workbench` with birth form (place search, coordinates fallback, settings presets, time-zone warnings), North, South and East Indian charts for D1 and any divisional chart, planet table to the arcsecond with KP lords, Vimshottari periods; tabs for yogas (with the evidence behind each and its citations), Shadbala and Ashtakavarga, Saturn and double transits, and KP (cusps, significators, ruling planets); birth-time sensitivity (how long the D1, D9, D10 and D60 lagnas and the Moon's pada hold, flagged when within the time's uncertainty); print or save as PDF; `/panchanga` (limbs with local end times, sunrise to moonset, the lunar and Tamil calendar, kalams, muhurtas, choghadiyas and horas; today's panchanga on arrival) and `/match` (both partners' birth data, Ashtakoota points by koota with the groom's and bride's attributes, doshas with their exceptions, Raman's ten kutas with reliefs, Kuja dosha of both charts, cited sources, selectable koota tables); site navigation; Playwright tests of every page on desktop and mobile with axe WCAG A/AA checks and no horizontal scroll |
| M8 | Knowledge base (about 1,000 rules) and prediction timeline | Done: 375 natal readings (house lords in houses after BPHS, grahas in houses after Phaladeepika, grahas in signs and the Moon's nakshatra after Brihat Jataka, rising signs), each paraphrased, cited and tested, served by `/v1/charts/readings`; 295 period rules (dasha results by lordship, placement, strength and antardasha pair; gochara from the Moon with vedha, Sade Sati, double transit, Jupiter and Saturn over natal grahas), read for any moment by `/v1/charts/period`; catalogue 982 rules; the promise × period × trigger timeline (`predict/`, `/v1/charts/predictions`): ten life domains month by month, windows with confidence (strong only when Vimshottari and Yogini agree and a transit confirms), evidence and matching rules, read by age; workbench tabs for the readings and the timeline (a heat map of the domains by year, each domain's promise and windows with their evidence, and what the running dasha and transits say now) |
| M9 | Birth-time rectification | Done: candidate times across the uncertainty window (up to ±3 hours) scored by how well the Vimshottari lords down to the sookshma signify each dated event, through the event's houses, karakas and divisional chart; optional Kunda, Pranapada and navamsa-gender checks; distinct ranked candidates with probability shares, the dashas at each event and what separates them; `/v1/rectify`, `/v1/people/{id}/rectify` (saved events) and the `/rectify` page. On synthetic charts whose events come from the engine's own rules it recovers the true time within 20 seconds from a recorded time up to 52 minutes off (about 0.3 s per run) |
| M10 | AI narrative and grounded chat | Done, except the live Claude eval: an evidence bundle with stable IDs (readings, yogas, each domain's promise and coming windows, the running periods and transits); every report paragraph and chat answer must cite IDs from it, and a server-side guard blocks death timing, medical, legal and financial directives, guaranteed outcomes and fear-based remedy selling; an offline template narrator (default, free) and a Claude narrator (only with `JYOTISH_API_ANTHROPIC_API_KEY`: cached system prompt, report schema as structured output through the Anthropic SDK, refusals handled with server-side fallbacks, one retry after failed checks); tool-grounded chat for any question in the person's own words, with seven lookup tools over the engine (planet, house, a date, periods, slow transits, a life area across the life, a year) and checked, cited answers, plus offline answers from the engine's facts; the chat in the consumer dashboard and the workbench; Message Batches requests for yearly pre-generation; `/v1/charts/report`, `/v1/charts/chat` and the workbench's Report tab. `scripts/narrative_eval.py`: the template passes 50 of 50 bundles; the Claude run (`--claude`) needs an API key |
| M11 | Consumer app (Hindi included) | Done: `/my` with guided onboarding (name, date, how the time is known and how exact it is, place; kept only on the device) and a plain-language dashboard: today (vara, tithi, nakshatra, Rahu kalam, the Moon's transit), this month (running dasha and its tenor, Sade Sati), the year ahead (each domain's strongest window, health left to the professional view), reminders with a calendar (.ics) download, a pointer to rectification when the time is uncertain. English and Hindi throughout the consumer pages, navigation, home, panchanga and matching (typed dictionaries, remembered per device; Devanagari names of grahas, signs, nakshatras, tithis and weekdays). The dashboard's sentences are built from structured results in either language; rule explanations and citations remain in English. Reminders can also arrive as browser notifications (Web Push, added with M12) |
| M12 | Accuracy Lab and production hardening | Done, except what needs the owner (below): the Accuracy Lab (backtests against shuffled-time and swapped-event controls, lift, permutation p-values, calibration by confidence; recorded-case format and a research-consented export; a synthetic check in `docs/ACCURACY_LAB.md`, which validates the pipeline only, as real results need recorded events); production hardening (an API image that downloads DE440 and checks its pinned SHA-256, runs as a non-root user and keeps its docs private; request IDs, JSON access lines and Prometheus metrics; security headers on the API and a content security policy with HSTS on the web app; body-size limits, a narrative quota, client addresses read safely behind proxies, verified TLS to Postgres, row-level security against Supabase's REST API); Web Push reminders for `/my` (the browser sends only its own reminder texts and times; RFC 8291 encryption checked against the RFC's test vector, VAPID signing, calls only to the browsers' push services, a scheduled sender that deletes what it sends); privacy notice and terms (drafts for legal review) linked from every page; dependency vulnerability audits in CI; the security review in [SECURITY.md](SECURITY.md) (ten findings, all fixed) and the deployment runbook in [RUNBOOK.md](RUNBOOK.md), whose first-deploy checklist is run on the first real deployment (no Docker daemon or hosting account in the build environment) |

## Acceptance criteria

| # | Criteria |
|---|---|
| M0 | CI green; licence guard passes |
| M1 | Planets and Moon ≤ 1″ vs oracle; ascendant ≤ 2″; Lahiri ≤ 0.5″; mean node ≤ 1″; true node ≤ 5″; sunrise ≤ 2 s with the same definition; Astronomy Engine within 1′ |
| M2 | 100% match with PyJHora fixtures, given identical longitudes |
| M3 | Dasha tables exact to the second vs oracle, given the same Moon longitude; ingress times ≤ 1 min |
| M4 | Shadbala within 1% of B.V. Raman's worked example and PyJHora; every rule's fixture tests pass |
| M5 | Panchanga spot checks (100 dates × 5 cities) match Drik Panchang to within 1 min, with the same sunrise definition |
| M6 | Contract tests pass; p95 chart response < 300 ms |
| M7 | Playwright end-to-end tests pass; WCAG AA; works on mobile |
| M8 | Rule tests pass; timeline is deterministic and explained |
| M9 | Recovers the true time within ±2 min on synthetic charts |
| M10 | 100% valid evidence IDs; 0 banned-claim hits on the eval set |
| M11 | Consumer end-to-end flows pass; Hindi UI complete |
| M12 | Security review clean; deployment runbook verified |

## What the owner needs to provide

- **Network access for this build environment:**
  - `naif.jpl.nasa.gov` for DE440.
  - `ssd.jpl.nasa.gov` for JPL Horizons.
  - `download.geonames.org` and `huggingface.co`.
- **Accounts:**
  - Supabase (Postgres and Auth).
  - An Anthropic API key.
  - Hosting: Vercel for the web app; Fly.io, Render or Cloud Run for the API.
  - A domain.
  - Payments (Razorpay or Stripe), if monetising.
- **Reviewers:**
  - A run of the check pairs in [MATCHING.md](MATCHING.md) on two or three of the large matchmaking apps, to confirm which reading of the Gana and Yoni tables they use (the build environment cannot reach them).
  - A qualified Jyotishi to review knowledge-base rules.
  - Legal review of terms, privacy policy and disclaimers.
- **Before launch** (see [RUNBOOK.md](RUNBOOK.md) and [SECURITY.md](SECURITY.md)):
  - The DE440 SHA-256, pinned from a trusted download.
  - The hosting and Supabase accounts, the database CA certificate and the production secrets.
  - A named grievance officer and breach-notification owner in the privacy notice.
  - Sign-in or payment in front of the narrative routes before turning on Claude, and the live Claude evaluation (`scripts/narrative_eval.py --claude`).
  - Recorded, consented life events for the Accuracy Lab; published accuracy claims need them.
  - A VAPID key pair and a scheduled job for `python -m jyotish_api.push send`, to turn on push reminders; a web app manifest and icons, so iPhones can receive them.
  - An independent penetration test.
