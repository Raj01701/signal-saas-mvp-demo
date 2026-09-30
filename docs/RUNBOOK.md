# Deployment and operations runbook

**What has been checked.** The pieces below were exercised in the build environment:
- The API test suite.
- The production web build under the end-to-end suite, with its security headers and content security policy.
- A Postgres 16 server with verified TLS: migrations up and down, the row-level-security check, and a round trip through the API.

**What still needs checking.** The container image has not been built, because the build environment has no Docker daemon. No hosted deployment exists yet. Work through the [first-deploy checklist](#10-first-deploy-checklist) on the first real deployment.

| Part | Where | Notes |
|---|---|---|
| Web app | Vercel (or any Node host) | `web/`, Next.js |
| API | Any container host: Fly.io, Render, Cloud Run | `api/Dockerfile` |
| Database | Postgres, such as Supabase | Migrations with Alembic |
| Sign-in | Supabase Auth | The API verifies its tokens |

## 1. Pin the DE440 checksum (once)

The image downloads NASA JPL's DE440 kernel (about 114 MB, covering 1550–2650) from NAIF at build time. The build fails unless the file's SHA-256 matches the value you pin.

1. On a machine you trust, download the kernel and hash it:

   ```sh
   curl -fLO https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de440.bsp
   sha256sum de440.bsp
   ```

2. Confirm the hash with a second download from another network.
3. Store it as a build variable, for example `DE440_SHA256` in CI or the host's build settings.

The build host needs access to `naif.jpl.nasa.gov`. Without DE440 the engine falls back to DE421, which covers only 1900–2053, and every result names the kernel it used.

## 2. Build and smoke-test the API image

Build from the repository root. The Dockerfile uses BuildKit, so Docker 23 or later is needed.

```sh
docker build -f api/Dockerfile --build-arg DE440_SHA256="$DE440_SHA256" -t jyotish-api:$(git rev-parse --short HEAD) .
docker run --rm -p 8000:8000 jyotish-api:<tag>
curl -s localhost:8000/health
curl -s localhost:8000/ready        # 503 for about 10 s while the gazetteer loads, then 200
curl -s -X POST localhost:8000/v1/charts -H 'content-type: application/json' \
  -d '{"birth":{"local_datetime":"1990-05-17T12:00:00","place":{"name":"New Delhi","latitude":28.6139,"longitude":77.209}}}' \
  | jq .ephemeris.name              # "DE440"
```

What the image does:
- Runs as an unprivileged user (uid 10001).
- Keeps the API docs private (`JYOTISH_API_PUBLIC_DOCS=false`).
- Requires verified TLS to Postgres (`JYOTISH_API_DATABASE_TLS=verify-full`).
- Turns off Uvicorn's own access log, which records client addresses. The API writes one JSON line per request instead.

## 3. Configure the API

Settings come from `JYOTISH_API_*` environment variables (`api/jyotish_api/config.py`). Put secrets in the host's secret store (Fly secrets, Render environment groups, Google Secret Manager), never in the image or the repository.

| Variable | Production value |
|---|---|
| `JYOTISH_API_DATABASE_URL` (secret) | `postgresql+pg8000://USER:PASSWORD@HOST:5432/postgres` |
| `JYOTISH_API_DATABASE_TLS` | `verify-full` (the image default) |
| `JYOTISH_API_DATABASE_CA_FILE` | Path to the database's CA certificate, mounted as a file (for Supabase, download it from the project's database settings) |
| `JYOTISH_API_SUPABASE_JWKS_URL` | `https://<project-ref>.supabase.co/auth/v1/.well-known/jwks.json` |
| `JYOTISH_API_SUPABASE_JWT_SECRET` (secret) | Only for projects still on the legacy shared JWT secret; leave it unset when using JWKS |
| `JYOTISH_API_CORS_ORIGINS` | The web origins as a JSON list, e.g. `["https://www.example.com"]` |
| `JYOTISH_API_FORWARDED_HOPS` | See [section 4](#4-client-addresses-behind-proxies) |
| `JYOTISH_API_RATE_LIMIT` | `120/minute` per client and route (the default) |
| `JYOTISH_API_NARRATIVE_RATE_LIMIT` | `60/hour` per client (the default); lower it when Claude is on |
| `JYOTISH_API_ANTHROPIC_API_KEY` (secret) | Optional; with `JYOTISH_API_NARRATIVE_PROVIDER=auto`, reports and chat use Claude |
| `JYOTISH_API_METRICS_TOKEN` (secret) | Required to read `/metrics` |
| `JYOTISH_API_MAX_BODY_BYTES` | `1000000` (the default) |

**Supabase notes**
- Direct database connections use IPv6. If the host has no IPv6 egress, use the connection pooler in session mode (port 5432).
- Test the CA file first with `psql "sslmode=verify-full sslrootcert=<file> host=<host> ..."`.

**Before enabling Claude publicly**, require sign-in, or a paid plan, for `/v1/charts/report` and `/v1/charts/chat`. Each call costs money, and a per-address limit does not stop abuse spread across many addresses.

## 4. Client addresses behind proxies

The rate limits count requests per client address. Behind a load balancer the connecting address is the proxy's, so the API reads `X-Forwarded-For` instead.

**How to set it.** Set `JYOTISH_API_FORWARDED_HOPS` to the number of proxies that append to that header. The API then takes the entry that many places from the right, which the outermost trusted proxy wrote and a client cannot forge. Typical values:
- 1 behind a single platform proxy.
- 2 behind a CDN or load balancer in front of the platform.

Check your platform's documentation for the exact value.

**Two ways to get it wrong:**
- **Too high:** clients can forge their address and escape the limits.
- **Too low** (0 behind a proxy): every client shares the proxy's budget.

**Verify after deploying.** This loop forges a new address on every request:

```sh
for i in $(seq 1 130); do
  curl -s -o /dev/null -w '%{http_code}\n' -H "X-Forwarded-For: 203.0.113.$((i % 250))" https://API/health
done | sort | uniq -c
```

- 429s must appear after about 120 requests. If none do, the value is too high.
- Then confirm that a request from a second network still gets 200 while the first is limited. If it doesn't, the value is too low.

**Scaling out.** Limits live in each process's memory. Several instances each allow the full limit. That is acceptable at launch; move to a shared store (slowapi's `storage_uri`, Redis) if abuse appears.

## 5. Database migrations

Run migrations before the new version takes traffic, for example as Fly's `release_command`, Render's pre-deploy command or a Cloud Run job. From the image:

```sh
docker run --rm -w /app/api -e JYOTISH_API_DATABASE_URL=... -e JYOTISH_API_DATABASE_CA_FILE=/certs/db-ca.crt \
  -v "$PWD/certs:/certs:ro" jyotish-api:<tag> alembic upgrade head
```

From a checkout, run `cd api && uv run alembic upgrade head` with the same variables.

**What revision 0002 does.** It enables row-level security on every table:
- Supabase's REST API, reachable with the public anon key, sees nothing.
- The API is unaffected, because it connects as the tables' owner.

Keep it that way. Do not add RLS policies for the `anon` or `authenticated` roles unless the web app starts reading tables directly.

**Keeping changes compatible.** Write each migration so the previous release still works against the new schema: add first, remove in a later release. Then a code rollback needs no schema rollback.

## 6. Deploy the web app (Vercel)

1. Set the project root to `web/`. The framework is Next.js, installed with `pnpm install --frozen-lockfile` and built with `pnpm build`.
2. Set `NEXT_PUBLIC_API_URL=https://api.example.com` for Production and Preview. It is read at build time: it goes into the client bundle and into the `connect-src` of the content security policy (`web/next.config.ts`), so changing it needs a rebuild.
3. Add the web origin to `JYOTISH_API_CORS_ORIGINS`. Preview deployments have their own origins: point them at a staging API, or add them to that API's list.

`next.config.ts` sets these headers on every page:
- The content security policy (scripts, styles and fonts from the site itself, API calls only to the configured API, no framing).
- HSTS for two years.
- `nosniff`, `DENY` framing and a strict referrer policy.
- A permissions policy with camera, microphone, geolocation and payment turned off.

Check them with `curl -sI https://www.example.com`.

## 7. Health, metrics and logs

**Health checks**
- `/health` is the liveness check and reports the API and engine versions. The container's `HEALTHCHECK` uses it.
- `/ready` returns 503 until startup work (the place gazetteer) is done. Point the platform's readiness or traffic check at it.

**Metrics**
- `/metrics` serves Prometheus text: requests by method, route template and status, and latency sums and counts.
- Send `Authorization: Bearer $JYOTISH_API_METRICS_TOKEN`.
- Counters are per process, so scrape every instance.
- Alert on a rising share of 5xx responses, on 429 bursts, and on p95 latency of `/v1/charts` above 300 ms (divide the latency sum by the count over a window).

**Logs**
- Every request produces one JSON line on standard output with `request_id`, `method`, `route` (the template, never a filled-in path), `status` and `ms`.
- Request bodies, birth data, tokens and client addresses are never logged.
- Every response carries `X-Request-ID`. A caller can send its own ID (1–64 characters from letters, digits, `.`, `_` and `-`); otherwise the API makes one.
- When a user reports a problem, ask for the ID and search the logs for it.

## 8. Backups and personal-data requests

**Backups**
- Turn on daily backups, plus point-in-time recovery if the plan offers it.
- Restore into a scratch project every quarter and run the round-trip test against it: `JYOTISH_API_TEST_POSTGRES_URL=... uv run pytest api/tests/test_account_api.py -k postgres`.
- Deleted data survives in backups until they expire. State that retention period in the privacy notice.

**Export.** Signed-in users download everything saved for them from `GET /v1/me/export`.

**Deletion**
- `DELETE /v1/me` removes the user's people, events and profile.
- The sign-in record lives in Supabase Auth. For a deletion request, also delete the user there, from the dashboard or with the service-role key.
- Requests made to the grievance contact: confirm the requester controls the account, act on it, and record the date.
- Confirm the deadlines under the DPDP Rules with counsel.

**Research data.** `scripts/export_research_cases.py` exports only consenting adults, without names or account IDs. Run it with the production settings from a trusted machine.

## 9. Incidents

1. **Contain**
   - Roll back by redeploying the previous image tag. Migrations are forward-compatible, per section 5.
   - Switch off the Claude narrator with `JYOTISH_API_NARRATIVE_PROVIDER=template`.
   - Lower the rate limits if the API is being abused.
2. **Rotate** whatever may be exposed: the database password, the Supabase signing keys, the Anthropic key and the metrics token.
3. **Investigate** with request IDs and the access lines.
4. **Notify** if personal data was breached. The DPDP Rules require telling the affected people and the Data Protection Board of India without delay, with a detailed report to the Board within 72 hours. CERT-In's directions require reporting certain cyber incidents within 6 hours. GDPR requires notice to the supervisory authority within 72 hours for EU users. Confirm the current obligations with counsel, and name who does this before launch.
5. **Write a short post-incident note** covering the timeline, cause and fixes, then track the fixes.

## 10. First-deploy checklist

- [ ] The image builds with the pinned hash, and a wrong hash fails the build.
- [ ] `/health` and `/ready` return 200, and a chart names `DE440`.
- [ ] API responses carry `x-request-id`, `nosniff`, `DENY` and `no-store`; `/docs` returns 404.
- [ ] `/metrics` returns 401 without the token.
- [ ] The forged `X-Forwarded-For` test in section 4 behaves as described.
- [ ] A 2 MB request body gets 413.
- [ ] The API sends no `access-control-allow-origin` for another origin, e.g. `curl -si -H 'Origin: https://example.org' https://API/health`.
- [ ] `alembic current` shows the head revision; the tables have row-level security on; the anon key reads nothing through Supabase's REST API.
- [ ] The web pages carry the security headers above, the browser console shows no policy violations, and `/my`, `/workbench` and `/panchanga` work against the production API.
- [ ] Backups are on and a restore has been tested.
- [ ] The owner-only items in [ROADMAP.md](ROADMAP.md) are done before public launch.
