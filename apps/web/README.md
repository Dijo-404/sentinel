# SN-038 / SN-012 — Mercury web shell + six role portals

**State:** Mercury landing + night portal shell; fixture identity auth UI; real-peers wires identity.v1 HTTP. Assembled product evidence is unverified. Money-path assembly is **not** claimed complete.

**Owned root:** `apps/web/`  
**Branch:** `feat/sn-012-mercury-ui`  
**Produces:** `web-shell.v1`  
**Consumes:** `case-api.v1`, `approval-ui.v1`, optional `voice.v1`, `identity.v1` (real-peers) / identity doubles (fixture)  
**Contract:** `sentinel.task-contracts.v1` · SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`

## Outcome

Mercury marketing landing at `/`, shared `/login` with workspace select, and six role portal trees (customer, merchant, operator, supervisor, risk, admin) behind a night sidebar shell (`AppSidebar` + `ProtectedShell`). Merchant, operator, and supervisor dashboards ship rich fixture viz (stat blocks, trend pills, chart cards). Customer self-registration and admin users/invite stay wired to the local identity stub. Role-specific `/<role>/login` routes redirect to `/login?portal=<role>`. Legacy `/intake` and `/ops` routes remain. Financial authority stays on the server; the UI masks PII and payment identifiers.

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

Open `http://localhost:3012/` for the Mercury landing. Use **Get started** / **Log in** → `http://localhost:3012/login` (workspace select + fixture demo credentials).

## Configuration

See `.env.example`.

| Variable | Purpose |
| --- | --- |
| `NEXT_PUBLIC_SHELL_MODE` | `fixture` (default) or `real-peers` |
| `NEXT_PUBLIC_VOICE_ENABLED` | `true` in `.env.example` for product demo; off unless set |
| `VOICE_BASE_URL` | Real-peers voice peer (default `http://127.0.0.1:8017`); BFF `/api/bff/voice` |
| `EVALS_BASE_URL` | Evals HTTP serve (default `http://127.0.0.1:8031`); BFF `/api/bff/evals` |
| `OBSERVABILITY_BASE_URL` | Observability peer (default `http://127.0.0.1:8033`); BFF `/api/bff/observability` |
| `PLATFORM_AI_BASE_URL` | Platform-ai peer (default `http://127.0.0.1:8036`); BFF `/api/bff/platform-ai` |
| `POLICY_BASE_URL` | Policy peer (default `http://127.0.0.1:8005`); BFF `/api/bff/policy` |
| `CASE_API_BASE_URL` | Required in real-peers mode |
| `CASE_API_BEARER_TOKEN` | Optional service-only fallback (server); portals use session cookie |
| `IDENTITY_BASE_URL` | Required in real-peers mode (default `http://127.0.0.1:8012`) |
| `IDENTITY_SANDBOX` / `SENTINEL_V1_SANDBOX` | Server-only: after verify/MFA/forgot, fetch sandbox inbox codes |
| `IDENTITY_SANDBOX_TOKEN` | Server-only token for password-reset inbox (never `NEXT_PUBLIC_*`) |

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

| Portal | Email | Password |
| --- | --- | --- |
| Customer | `customer@example.test` | `demo-customer` |
| Merchant | `merchant@example.test` | `demo-merchant` |
| Operator | `operator@example.test` | `demo-operator` |
| Supervisor | `supervisor@example.test` | `demo-supervisor` |
| Risk | `risk@example.test` | `demo-risk` |
| Admin | `admin@example.test` | `demo-admin` |

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

| Route | Role |
| --- | --- |
| `/` | Mercury landing (night marketing) |
| `/login` | Shared login + workspace select (`?portal=` preselect; `?next=` safe redirect) |
| `/customer/login` → `/login?portal=customer` | Customer (redirect) |
| `/merchant/login` → `/login?portal=merchant` | Merchant (redirect) |
| `/operator/login` → `/login?portal=operator` | Support Operator (redirect) |
| `/supervisor/login` → `/login?portal=supervisor` | Supervisor (redirect) |
| `/risk/login` → `/login?portal=risk` | Risk Officer (redirect) |
| `/admin/login` → `/login?portal=admin` | Platform Admin (redirect) |
| `/customer/register` · `/customer/dashboard` | Customer register + protected shell |
| `/merchant/dashboard` | Merchant overview (rich viz) |
| `/operator/dashboard` · `/operator/queue` | Operator overview (rich viz) + queue |
| `/supervisor/dashboard` | Supervisor overview (rich viz) |
| `/supervisor/team` | Ops roster via `/api/bff/identity` → `GET /v1/ops/team` (fail closed) |
| `/supervisor/approvals` · `/supervisor/approvals/[actionId]` | Supervisor approval queue + exact decide UI (local substitute) |
| `/supervisor/cases/[caseId]` | Supervisor case review with opt-in approval slot |
| `/risk/dashboard` | Risk Officer |
| `/risk/queue` · `/holds` · `/transactions` · `/audit` · `/analytics` · `/reports` | Risk lists/KPIs via `/api/bff/risk` (fail closed) |
| `/admin/dashboard` | Platform Admin |
| `/admin/users` · `/admin/users/invite` | Staff directory + invite (stub) |
| `/auth/workspaces` · `/auth/verify` · `/auth/mfa` · `/auth/forgot-password` · `/auth/reset-password` · `/auth/accept-invitation` | Identity auth flows (forgot/reset via IdentityClient server actions; workspaces/verify/MFA need session) |
| `/unauthorized` | Role mismatch — authorized workspaces only |
| `/intake` | Legacy customer text intake (requires customer session) |
| `/cases/[caseId]` | Case timeline (requires customer session) |
| `/ops` | Legacy operator queue (requires operator or supervisor) |
| `/ops/cases/[caseId]/evidence` | Evidence only (no approve controls; operator-safe) |
| `/v1/capabilities` | Assembly probe |

Staff portals have **no** public sign-up. Customer registration rejects privileged fields (`roles`, `tenant_id`, `subject_refs`). Admin invite rejects `role_id=customer`. Protected portals use the night sidebar shell; financial authority remains server-side.

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

| Dimension | This module check |
| --- | --- |
| Component under test | Real web-shell + Mercury portal scaffold |
| Case API peer | Local fixture stub (+ real-peer adapter unit doubles) |
| Identity peer | Local fixture stub (+ real-peer HTTP adapter with fetch doubles) |
| Approval UI | Local substitute / package (Task 8) |
| Voice | BFF peer client when enabled; fixture stub in fixture mode |
| Payment provider | N/A (UI only) |
| Model/voice live Sarvam | Off for `make check` |
| Money-path assembly | **Not claimed** |

Assembled live identity + case-api integration remains **unverified** until owner assembly.
