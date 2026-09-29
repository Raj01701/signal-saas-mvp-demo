# Roadmap

Each milestone ends tested, committed and pushed. The status column is kept current.

| # | Milestone | Status |
|---|---|---|
| M0 | Foundation: monorepo, tooling, CI, licence guard, research, README | Done |
| M1 | Astronomy and place core, plus the oracle harness and golden fixtures | Done: see [ACCURACY.md](ACCURACY.md) |
| M2 | Jyotish basics: nakshatras, vargas, dignity, avasthas, special points | Planned |
| M3 | Timing: dashas, transits, Varshaphal and Tajika | Planned |
| M4 | Strength and yogas: Shadbala, Ashtakavarga, rule DSL, 300+ yogas | Planned |
| M5 | Panchanga, matchmaking, KP | Planned |
| M6 | API and data layer: FastAPI, Postgres, auth, caching | Planned |
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
