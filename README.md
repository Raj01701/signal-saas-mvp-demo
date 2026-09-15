# Signal — SaaS MVP demo

A working proof-of-concept feedback & feature-request tracker, built to show the spine of a multi-tenant SaaS MVP: real auth, a Postgres database, a server-side API that enforces roles, and a polished UI.

**Live:** https://saas-mvp-signal.vercel.app

## What's inside
- `index.html` — marketing/landing page with a live embed of the app
- `app.html` — the app: email sign-up/sign-in or guest access, dashboard (trend chart, top voted, status breakdown), submissions with search/sort/filter/upvote/status workflow, admin (invite, roles, enable/disable), light/dark themes, mobile + desktop
- `api/` — Node serverless REST API on Vercel (`health`, `config`, `me`, `submissions`, `users`, `stats`)
- `logic.js` — pure, DOM-free core logic shared by the browser and the API (permissions, validation, status workflow, stats)
- `logic.test.mjs` — unit tests for the core logic
- `supabase/schema.sql` — tables, row-level security, sign-up trigger and seed data

## How it works
- **Auth** — Supabase Auth: email + password (no confirmation step, for demo speed) or anonymous guest sessions.
- **Tenancy** — a database trigger gives every new user their own workspace, as Owner, seeded with sample requests and teammates.
- **API** — the browser sends its Supabase access token to `/api`; each function verifies it, loads the caller's membership and scopes every query to their workspace. Owners/Admins manage status, deletes and members; Members add and upvote; Viewers are read-only.
- **Database lockdown** — RLS is enabled with no policies and table grants are revoked from `anon`/`authenticated`, so the public anon key cannot read or write tables directly. Only the API, holding the service-role key server-side, can.
- **Concurrency** — upvotes are an atomic SQL increment; status changes are conditional on the status that was read, returning 409 if someone changed it first.

## Setup
1. Create a Supabase project and run `supabase/schema.sql` in the SQL editor.
2. In Auth settings, enable anonymous sign-ins and turn off email confirmation.
3. Set Vercel environment variables: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` (server-only).

## Run locally
```bash
npm install
vercel dev      # serves the pages and /api with the env vars above
npm test        # unit tests
```

Accessibility targets WCAG AA in both themes.
