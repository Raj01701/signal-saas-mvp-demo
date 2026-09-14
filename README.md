# Signal — SaaS MVP demo

A working proof-of-concept feedback & feature-request tracker, built to show the spine of a single-workspace SaaS MVP.

**Live:** https://saas-mvp-signal.vercel.app

## What's inside
- `index.html` — premium marketing/landing page (offline, honest copy, live embed of the app)
- `app.html` — the app: email auth, dashboard, CRUD with a status workflow, admin view, light/dark themes, mobile + desktop
- `logic.js` — pure, DOM-free core logic (status transitions, counts, dates)
- `logic.test.mjs` — unit tests for the core logic

## Run locally
```bash
# serve the folder over http (ES modules need http, not file://)
npx serve .        # or: python3 -m http.server
# run tests
node --test
```

## Notes
Front-end proof-of-concept: data is stored in the browser (localStorage) and sign-in is simulated. A production build would use Next.js + Supabase (Postgres, REST). Accessibility targets WCAG AA in both themes.
