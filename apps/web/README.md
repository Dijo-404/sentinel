# SN-038 / SN-012 — Mercury web shell + six role portals

**State:** Mercury landing + night portal shell; fixture identity auth UI; real-peers wires identity.v1 HTTP. Assembled product evidence is unverified. Money-path assembly is **not** claimed complete.

**Owned root:** `apps/web/`  
**Branch:** `feat/sn-012-mercury-ui`  
**Produces:** `web-shell.v1`  
**Consumes:** `case-api.v1`, `approval-ui.v1`, optional `voice.v1`, `identity.v1` (real-peers) / identity doubles (fixture)  
**Contract:** `sentinel.task-contracts.v1` · SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`

## Outcome

Mercury marketing landing at `/`, shared email/password-only `/login`, and six role portal trees (customer, merchant, operator, supervisor, risk, admin) behind a night sidebar shell (`AppSidebar` + `ProtectedShell`). Merchant, operator, and supervisor dashboards ship rich fixture viz (stat blocks, trend pills, chart cards). Customer and merchant self-registration use `/signup`; fixture mode uses local identity doubles and real-peers uses identity HTTP. Role-specific `/<role>/login` routes redirect to `/login?portal=<role>`. Legacy `/intake` and `/ops` routes remain. Financial authority stays on the server; the UI masks PII and payment identifiers.

## Standalone setup

Requires Node.js 20+.

```sh
cd apps/web
cp .env.example .env   # optional; defaults to fixture mode
make check             # npm ci + tsc + vitest
```

Preview (after check/build):

```sh
make -C apps/web preview
# or: npm run dev
```

Open `http://localhost:3012/` for the Mercury landing. Use **Get started** / **Log in** → `http://localhost:3012/login` (email + password). One assigned workspace opens its portal; several open `/auth/workspaces`, listing only that account’s assignments.

## Configuration

See `.env.example`.

| Variable                                   | Purpose                                                                            |
| ------------------------------------------ | ---------------------------------------------------------------------------------- |
| `NEXT_PUBLIC_SHELL_MODE`                   | `fixture` (default) or `real-peers`                                                |
| `NEXT_PUBLIC_VOICE_ENABLED`                | `true` in `.env.example` for product demo; off unless set                          |
| `VOICE_BASE_URL`                           | Real-peers voice peer (default `http://127.0.0.1:8017`); BFF `/api/bff/voice`      |
| `EVALS_BASE_URL`                           | Evals HTTP serve (default `http://127.0.0.1:8031`); BFF `/api/bff/evals`           |
| `OBSERVABILITY_BASE_URL`                   | Observability peer (default `http://127.0.0.1:8033`); BFF `/api/bff/observability` |
| `PLATFORM_AI_BASE_URL`                     | Platform-ai peer (default `http://127.0.0.1:8036`); BFF `/api/bff/platform-ai`     |
| `POLICY_BASE_URL`                          | Policy peer (default `http://127.0.0.1:8005`); BFF `/api/bff/policy`               |
| `CASE_API_BASE_URL`                        | Required in real-peers mode                                                        |
| `CASE_API_BEARER_TOKEN`                    | Optional service-only fallback (server); portals use session cookie                |
| `IDENTITY_BASE_URL`                        | Required in real-peers mode (default `http://127.0.0.1:8012`)                      |
| `IDENTITY_SANDBOX` / `SENTINEL_V1_SANDBOX` | Server-only: after verify/MFA/forgot, fetch sandbox inbox codes                    |
| `IDENTITY_SANDBOX_TOKEN`                   | Server-only token for password-reset inbox (never `NEXT_PUBLIC_*`)                 |

Real-peer failures are visible. Never put bearers, identity passwords, or session tokens in `NEXT_PUBLIC_*`. Fixture auth uses `tests/stubs/identity` seeded users. Real-peers calls identity.v1 (`/v1/auth/login|me|workspaces|accept-invitation`, register, admin invite) via the server-only identity client; the httpOnly `sentinel_session` cookie stores the identity `session_token`. Portal case-api traffic goes through `/api/bff/case/**`, which forwards that session as the case-api bearer (one principal per request). Supervisor Team uses `/api/bff/identity/**` → `GET /v1/ops/team` (supervisor-safe tenant roster; does **not** call `/v1/admin/users`, which remains platform_admin-only).

### Sandbox auth challenge demo

With identity `IDENTITY_SANDBOX=1` (or `SENTINEL_V1_SANDBOX=1`) and matching web
server env + `IDENTITY_SANDBOX_TOKEN`:

1. Sign in → `/auth/verify` or `/auth/mfa` → Request challenge.
2. Server action calls `GET /v1/auth/sandbox/latest-code` and shows the code
   (no `IDENTITY_EXPOSE_SANDBOX_CODES` required; works in real-peers Postgres).
3. Forgot password → server action may call
   `GET /v1/auth/sandbox/password-reset-code` with the server token and show the
   code on the success banner → `/auth/reset-password`.

### Fixture demo credentials (synthetic only)

| Portal     | Email                     | Password          |
| ---------- | ------------------------- | ----------------- |
| Customer   | `customer@example.test`   | `demo-customer`   |
| Merchant   | `merchant@example.test`   | `demo-merchant`   |
| Operator   | `operator@example.test`   | `demo-operator`   |
| Supervisor | `supervisor@example.test` | `demo-supervisor` |
| Risk       | `risk@example.test`       | `demo-risk`       |
| Admin      | `admin@example.test`      | `demo-admin`      |

## Layout

- `src/domain/` — wire types, masking, status labels (framework-free)
- `src/application/ports.ts` — CaseClient / slot ports
- `src/adapters/` — fixture + real-peer clients, composition
- `src/lib/server/` — session cookie helpers, authorization, auth actions
- `src/components/marketing/` — Mercury landing + hero
- `src/components/shell/` — night `AppSidebar`
- `src/components/viz/` — shared fixture chart/stat primitives
- `src/components/auth|layout|identity|dashboards/` — login, protected shell, portal overviews
- `src/app/{customer,merchant,operator,supervisor,risk,admin}/` — portal trees
- `src/slots/` — local approval-ui / voice substitutes
- `tests/stubs/` — case-api, approval-ui, voice, **identity** doubles

## Routes

| Route                                                                                                                            | Role                                                                                                     |
| -------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `/`                                                                                                                              | Mercury landing (night marketing)                                                                        |
| `/login`                                                                                                                         | Email + password login; identity assignments choose portal (`?next=` role-scoped)                        |
| `/customer/login` → `/login?portal=customer`                                                                                     | Customer (redirect)                                                                                      |
| `/merchant/login` → `/login?portal=merchant`                                                                                     | Merchant (redirect)                                                                                      |
| `/operator/login` → `/login?portal=operator`                                                                                     | Support Operator (redirect)                                                                              |
| `/supervisor/login` → `/login?portal=supervisor`                                                                                 | Supervisor (redirect)                                                                                    |
| `/risk/login` → `/login?portal=risk`                                                                                             | Risk Officer (redirect)                                                                                  |
| `/admin/login` → `/login?portal=admin`                                                                                           | Platform Admin (redirect)                                                                                |
| `/customer/register` · `/customer/dashboard`                                                                                     | Legacy registration redirects to `/signup?type=customer`; protected dashboard                            |
| `/merchant/dashboard`                                                                                                            | Merchant overview (rich viz)                                                                             |
| `/operator/dashboard` · `/operator/queue`                                                                                        | Operator overview (rich viz) + queue                                                                     |
| `/supervisor/dashboard`                                                                                                          | Supervisor overview (rich viz)                                                                           |
| `/supervisor/team`                                                                                                               | Ops roster via `/api/bff/identity` → `GET /v1/ops/team` (fail closed)                                    |
| `/supervisor/approvals` · `/supervisor/approvals/[actionId]`                                                                     | Supervisor approval queue + exact decide UI (local substitute)                                           |
| `/supervisor/cases/[caseId]`                                                                                                     | Supervisor case review with opt-in approval slot                                                         |
| `/risk/dashboard`                                                                                                                | Risk Officer                                                                                             |
| `/risk/queue` · `/holds` · `/transactions` · `/audit` · `/analytics` · `/reports`                                                | Risk lists/KPIs via `/api/bff/risk` (fail closed)                                                        |
| `/admin/dashboard`                                                                                                               | Platform Admin                                                                                           |
| `/admin/users` · `/admin/users/invite`                                                                                           | Staff directory + invite (stub)                                                                          |
| `/auth/workspaces` · `/auth/verify` · `/auth/mfa` · `/auth/forgot-password` · `/auth/reset-password` · `/auth/accept-invitation` | Identity auth flows (forgot/reset via IdentityClient server actions; workspaces/verify/MFA need session) |
| `/unauthorized`                                                                                                                  | Role mismatch — authorized workspaces only                                                               |
| `/intake`                                                                                                                        | Legacy customer text intake (requires customer session)                                                  |
| `/cases/[caseId]`                                                                                                                | Case timeline (requires customer session)                                                                |
| `/ops`                                                                                                                           | Legacy operator queue (requires operator or supervisor)                                                  |
| `/ops/cases/[caseId]/evidence`                                                                                                   | Evidence only (no approve controls; operator-safe)                                                       |
| `/v1/capabilities`                                                                                                               | Assembly probe                                                                                           |

Public `/signup` offers Customer | Merchant tabs (arrow keys, Home/End) and prefills `?email=`; `?type=merchant` selects merchant. Customer and merchant submit to `/v1/auth/customer/register` and `/v1/auth/merchant/register`, respectively. Business name is required for merchant signup. Staff roles (operator, supervisor, risk officer, platform admin) have **no** public sign-up. Registration rejects privileged fields (roles, tenant, subject and merchant references); identity assigns scope server-side. Admin invite rejects `role_id=customer`. Protected portals use the night sidebar shell; financial authority remains server-side.

## Login enumeration and trusted ingress

Owner-approved trade-off (#154): identity returns `ACCOUNT_NOT_FOUND` for an unknown email and the web redirects to `/signup?email=<encoded-email>`. This deliberately reveals whether an account exists. Existing-account wrong passwords remain generic. Identity applies login limits per client IP and email/IP pair; when trustworthy client IP is absent, it uses per-email failed-response throttling. The email appears in the signup URL; redact authentication query strings from access logs and analytics.

Identity login validation rejections (HTTP 422 or `INVALID_INPUT`) use the same
generic invalid-credentials result as wrong passwords. Rate limiting retains its
distinct result, and unrelated identity outages remain availability errors.

The Next server action does not expose its transport peer address. Arbitrary incoming `X-Forwarded-For` is **never** trusted or copied. Forwarding is disabled unless the web has a server-only `WEB_TRUSTED_INGRESS_TOKEN` (at least 32 random characters), and an explicitly configured ingress authenticates each request with `X-Sentinel-Ingress-Token` plus a single literal `X-Sentinel-Client-IP` (IPv4 or IPv6). The web compares the token in constant time and only then forwards that IP as `X-Forwarded-For` to identity login. Missing, malformed or unauthenticated context omits the forwarded header. The ingress token is never forwarded to identity or sent to the browser.

Deployment must configure the ingress to **strip and overwrite both Sentinel headers**, derive the address from its own verified transport/proxy trust configuration, keep its token server-side, redact the token from logs and use private/TLS transport to the BFF. Limit direct access to the web origin. Configure identity's server-only `IDENTITY_TRUSTED_PROXIES` with the exact BFF socket addresses (empty by default); identity trusts the forwarded IP only from those peers. For a configured BFF without a valid client address, identity uses the unknown-client/email fallback and avoids a shared BFF-IP bucket. This PR changes no ingress, compose or deployment configuration. Per-client-IP limits across the assembled proxy chain require that separate deployment setup and verification; fixture doubles do not prove rate limiting.

## Assembly probe

```http
GET /v1/capabilities
```

`mode` comes from `NEXT_PUBLIC_SHELL_MODE` (`fixture` | `real-peers`). App stays on port **3012**.

## Checks observed

```sh
make -C apps/web check
```

Independence: installs only `apps/web` dependencies; uses local stubs under `tests/stubs/`; no sibling Sentinel services required.

Root `make check` validates repository metadata only.

## Evidence labels

| Dimension               | This module check                                                |
| ----------------------- | ---------------------------------------------------------------- |
| Component under test    | Real web-shell + Mercury portal scaffold                         |
| Case API peer           | Local fixture stub (+ real-peer adapter unit doubles)            |
| Identity peer           | Local fixture stub (+ real-peer HTTP adapter with fetch doubles) |
| Approval UI             | Local substitute / package (Task 8)                              |
| Voice                   | BFF peer client when enabled; fixture stub in fixture mode       |
| Payment provider        | N/A (UI only)                                                    |
| Model/voice live Sarvam | Off for `make check`                                             |
| Money-path assembly     | **Not claimed**                                                  |

Assembled live identity + case-api integration remains **unverified** until owner assembly.

## Deployed role journey checks

The optional Playwright runner exercises all six seeded sandbox accounts,
implemented portal routes, desktop/mobile rendering, role isolation, persisted
login, logout, keyboard palette, theme persistence and mobile navigation.

```sh
uv run --with playwright playwright install chromium
uv run --with playwright python apps/web/scripts/role-journeys.py \
  --base-url http://65.2.68.199 --output-dir /tmp/sentinel-role-journeys
```

Use only a synthetic sandbox containing the documented seed identities. The
runner stores screenshots and redacted request metadata, never session cookies.
`--browser-executable /path/to/chromium` selects an existing browser if needed.
See [the audit](docs/role-user-journeys.md) for evidence and limits.

HTTP-only synthetic demos require both `SENTINEL_V1_SANDBOX=1` and
`WEB_ALLOW_HTTP_SANDBOX=1` to issue a non-Secure session cookie. Leave the HTTP
flag disabled for HTTPS and non-sandbox deployments. These flags do not grant
roles or payment authority.

Optional opaque peer credentials also require `SENTINEL_V1_SANDBOX=1` plus
`WEB_SANDBOX_PEER_BINDINGS`, keyed by identity user ID with exact `tenant_id`,
`role_id`, and optional `merchant_ref`. Each proxy restricts the permitted roles.
An unmatched user, tenant, merchant, role or unavailable identity retains the
original caller session, so configured demo credentials cannot elevate it.
`MERCHANT_TEAMS_TOKEN_admin` supplies the separate admin bridge credential.
Keep all such values server-side. Fresh merchant accounts need their own peer
provisioning; they never inherit the demo merchant's records.
