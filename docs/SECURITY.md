# Security review

**Reviewed:** 30 September 2026, at milestone M12.

**Scope:**
- The API: routes, authentication, authorization, limits, proxies, logging, database access and outbound calls.
- The engine's input handling.
- The web app's headers.
- The container.
- Dependencies.

**Method:**
- The bandit rule set (ruff `S`) over all Python code.
- `pip-audit` on the exported runtime requirements and `pnpm audit --prod` on the web app. Both are now CI steps.
- A manual review of the areas above.
- Tests for each fix, including a Postgres 16 server with its own certificate authority for the TLS and row-level-security checks.

**Result:** every finding is fixed or accepted, as listed below. No known vulnerabilities in runtime dependencies on the review date.

## Findings

| # | Finding | Severity | Status |
|---|---|---|---|
| 1 | The container trusted every `X-Forwarded-For` entry (`--forwarded-allow-ips *`). Uvicorn then takes the leftmost entry, which the client writes, so any client could pick a fresh rate-limit bucket per request. | High | **Fixed.** The client address comes from `JYOTISH_API_FORWARDED_HOPS` entries from the right, written by trusted proxies (`ratelimit.py`). The flag is gone from the image. Tests show forged prefixes neither escape nor share a limit. |
| 2 | The body-size limit checked only the declared `Content-Length`, so chunked bodies of any size reached the parser. | Medium | **Fixed.** Streamed bytes are counted as they arrive and refused with 413. The rate limiter moved to slowapi's pure-ASGI middleware, whose predecessor turned that refusal into a 400. |
| 3 | The report and chat routes may call a paid model. They shared the general limit of 120 per minute per route, and chat messages had no length cap. | Medium | **Fixed.** They have their own per-client quota (`JYOTISH_API_NARRATIVE_RATE_LIMIT`, default 60 per hour). Chat takes at most 20 messages of up to 4,000 characters. **Residual:** per-address limits cannot stop abuse spread across many addresses, so require sign-in or payment before enabling Claude publicly (see [RUNBOOK.md](RUNBOOK.md)). |
| 4 | Postgres connections used the driver's default TLS: encrypted when offered, but the certificate unchecked, so open to interception. | Medium | **Fixed.** `JYOTISH_API_DATABASE_TLS=verify-full` (the image default) requires TLS and checks the certificate and host name against `JYOTISH_API_DATABASE_CA_FILE`. It applies to both the API and the migrations. Tested against a local server: the right CA connects; a wrong CA and the system CAs are refused. |
| 5 | On Supabase, the tables in the `public` schema would be readable through Supabase's REST API with the public anon key. | High (when deployed on Supabase) | **Fixed.** Migration 0002 enables row-level security with no policies on every table. The API connects as the owner and is unaffected. The Postgres test checks it. |
| 6 | The JSON access lines were logged below the root logger's level, so production had no request log at all. | Low | **Fixed.** The access logger has its own handler; a test checks the lines. |
| 7 | Uvicorn's own access log records client addresses, which the service does not need to keep. | Low (privacy) | **Fixed.** It is off in the image; the API's JSON line has no address. |
| 8 | `/metrics` was public. | Low | **Fixed.** Set `JYOTISH_API_METRICS_TOKEN` to require a bearer token (compared in constant time). |
| 9 | Three engine invariants were `assert` statements, which Python removes under `-O`. | Low | **Fixed.** They are explicit `ValueError`s (varga starting sign, time-zone offset, day or night fraction in Shadbala). |
| 10 | The narrative transport would call any URL scheme. | Low | **Fixed.** HTTPS only. |

**Accepted rule findings**, none of which is a vulnerability:
- `assert` in tests and scripts (S101).
- Pseudo-random sampling in the Accuracy Lab and evaluation scripts (S311): statistics, not secrets.
- A partial executable path in the development-only licence script (S607).
- Fixed secrets inside tests (S105, S106).

## Controls in place

**Authentication**
- Supabase access tokens are verified locally (`auth.py`) with pinned algorithms: HS256 with the project secret, or RS256 and ES256 from its JWKS.
- The audience is checked, and `sub` and `exp` are required.
- Invalid tokens get 401.

**Authorization**
- Every saved person and event is looked up with its owner.
- Another user's ID gets 404, so the API does not reveal that the record exists.
- A minor's data needs the guardian's consent.

**Input**
- Pydantic validates every body.
- Engine `ValueError`s (dates outside the ephemeris, polar days, unknown options) become 422.
- Rectification windows and prediction spans are capped.
- Uvicorn bounds concurrent connections to 200.

**Abuse**
- 120 requests per minute per client and route, plus the narrative quota.
- Bodies up to 1 MB.

**Browser**
- The API allows only the configured web origins, without credentials.
- API responses carry `nosniff`, `DENY` framing, `no-referrer` and `no-store`.
- The web app sends a content security policy:
  - Scripts, styles and fonts from the site itself.
  - Connections only to the configured API.
  - No objects, no framing, and forms only to itself.
- It also sends HSTS, `nosniff`, `DENY` framing, a strict referrer policy and a permissions policy.

**Secrets**
- All secrets come from the environment and never enter logs or responses.
- The Anthropic call uses HTTPS with the standard library.

**Personal data**
- Without an account, birth details stay in the browser.
- Logs hold no bodies, birth data or client addresses.
- Research export includes only consenting adults, without names or IDs.
- Users can export and delete their data.

**Push reminders** (added after the review)
- The server calls only the browsers' push services: HTTPS on the default port, with no credentials in the URL. It checks this when a subscription is saved and again when sending, so the API cannot be pointed at internal or arbitrary addresses.
- Messages are encrypted for the browser (RFC 8291, checked against the RFC's test vector) and signed with the operator's VAPID key.
- Replacing a subscription's keys or unsubscribing requires its authentication secret.
- No birth details are stored. Reminders are deleted once sent, idle subscriptions are forgotten, and the tables have row-level security.
- The service worker runs under its own strict content security policy and only opens pages of the site itself.

**Supply chain**
- Pinned lockfiles (`uv.lock`, `pnpm-lock.yaml`).
- The licence guard, and vulnerability audits in CI.
- The DE440 kernel is checked against a pinned SHA-256 at image build.
- The image runs as a non-root user.

## Known limits and follow-ups

- **Script policy.** The content security policy allows inline scripts, which Next.js's static pages need. A nonce-based policy would require rendering every page on request. Revisit this if the app ever shows content written by other users.
- **Rate limits are per process.** Move them to a shared store when running several instances.
- **Before launch:**
  - Commission an independent penetration test.
  - Run Supabase's security advisor on the production project.
  - Have counsel review the privacy notice and terms (both marked as drafts).
- **Account sign-in in the web app** is not built yet. When it is:
  - Keep tokens out of `localStorage` if possible.
  - Keep the policy's `connect-src` to the API and Supabase Auth only.

## Reporting a vulnerability

Until a security contact is published on the site, report privately to the repository owner rather than in a public issue.
