# Jyotish Platform

A precise, explainable Vedic astrology (Jyotish) platform:

- **Engine** (`engine/`): the deterministic Python calculation engine. It uses NASA JPL ephemerides through Skyfield, and every shipped dependency is permissively licensed.
- **API** (`api/`): FastAPI service.
- **Web** (`web/`): Next.js app. The professional astrologer workbench comes first, then the consumer experience.
- **Knowledge base** (`knowledge/`): classical rules, each paraphrased and cited to its source text.

> This repository previously held only the README of the "Signal" SaaS demo. It is now
> the monorepo for the Jyotish platform, and can be renamed on GitHub at any time.

## Why it is different

- **Calculations you can trust:** sub-arcsecond planet positions, historically correct time zones (including Bombay Time, Calcutta Time and India's 1942–45 war time), and transparent settings.
- **Birth-time sensitivity and rectification:** the app tells you which factors depend on an uncertain birth time.
- **Explainable readings:** every statement cites the rule and classical text behind it.
- **Honest accuracy:** no guaranteed predictions. Hit rates are measured against controls.

Read [`docs/RESEARCH.md`](docs/RESEARCH.md) for the research behind these choices, [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the design, and [`docs/ROADMAP.md`](docs/ROADMAP.md) for milestones and status.

## Develop

```bash
# Python engine + API (uv workspace)
uv sync
uv run ruff check . && uv run mypy engine/jyotish_engine api/jyotish_api
uv run pytest
uv run python scripts/check_licenses.py          # licence guard (runtime deps)

# API server
uv run uvicorn jyotish_api.main:app --reload

# Web app
pnpm -C web install
pnpm -C web dev            # http://localhost:3000
pnpm -C web lint && pnpm -C web typecheck && pnpm -C web test
```

### Ephemeris

The engine uses NASA JPL **DE440** in production. To use it locally, download `de440.bsp` from `https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/` and either place it in `data/ephemeris/` or point `JYOTISH_EPHEMERIS` at it.

Without it, the engine falls back to DE421 (1899-07-28 to 2053-10-08), which the `skyfield-data` package bundles.

## Data credits

- Planetary ephemerides: NASA JPL.
- Places: [GeoNames](https://www.geonames.org/) (CC BY 4.0).
- Timezone boundaries: timezone-boundary-builder / OpenStreetMap contributors (ODbL).
