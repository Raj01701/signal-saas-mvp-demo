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
| M7 | Pro workbench web app | Planned |
| M8 | Knowledge base (about 1,000 rules) and prediction timeline | Planned |
| M9 | Birth-time rectification | Planned |
| M10 | AI narrative and grounded chat | Planned |
| M11 | Consumer app (Hindi included) | Planned |
| M12 | Accuracy Lab and production hardening | Planned |

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
  - A qualified Jyotishi to review knowledge-base rules.
  - Legal review of terms, privacy policy and disclaimers.
