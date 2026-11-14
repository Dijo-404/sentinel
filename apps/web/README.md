# SN-038 / SN-012 — Six role portals + web shell

**State:** portal scaffold + fixture identity auth UI; real-peers wires identity.v1 HTTP. Assembled product evidence is unverified. Money-path assembly is **not** claimed complete.

**Owned root:** `apps/web/`  
**Branch:** `feat/web-identity-real-peer`  
**Produces:** `web-shell.v1`  
**Consumes:** `case-api.v1`, `approval-ui.v1`, optional `voice.v1`, `identity.v1` (real-peers) / identity doubles (fixture)  
**Contract:** `sentinel.task-contracts.v1` · SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`

## Outcome

Six role portal trees (customer, merchant, operator, supervisor, risk, admin) with shared `RoleLogin`, customer self-registration, protected layouts, and admin users/invite wired to a local identity stub. Legacy `/intake` and `/ops` routes remain. Financial authority stays on the server; the UI masks PII and payment identifiers.

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

Open `http://localhost:3012/` for portal entry.

## Configuration

See `.env.example`.

| Variable | Purpose |
| --- | --- |
| `NEXT_PUBLIC_SHELL_MODE` | `fixture` (default) or `real-peers` |
| `NEXT_PUBLIC_VOICE_ENABLED` | `false` by default |
| `CASE_API_BASE_URL` | Required in real-peers mode |
| `CASE_API_BEARER_TOKEN` | Optional service-only fallback (server); portals use session cookie |
| `IDENTITY_BASE_URL` | Required in real-peers mode (default `http://127.0.0.1:8012`) |

Real-peer failures are visible. Never put bearers, identity passwords, or session tokens in `NEXT_PUBLIC_*`. Fixture auth uses `tests/stubs/identity` seeded users. Real-peers calls identity.v1 (`/v1/auth/login|me|workspaces|accept-invitation`, register, admin invite) via the server-only BFF; the httpOnly `sentinel_session` cookie stores the identity `session_token`. Portal case-api traffic goes through `/api/bff/case/**`, which forwards that session as the case-api bearer (one principal per request).

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
- `src/components/auth|layout|identity|dashboards/` — shared portal UI
- `src/app/{customer,merchant,operator,supervisor,risk,admin}/` — portal trees
- `src/slots/` — local approval-ui / voice substitutes
- `tests/stubs/` — case-api, approval-ui, voice, **identity** doubles

## Routes

| Route | Role |
| --- | --- |
| `/` | Portal entry |
| `/customer/login` · `/customer/register` · `/customer/dashboard` | Customer |
| `/merchant/login` · `/merchant/dashboard` | Merchant |
| `/operator/login` · `/operator/dashboard` | Support Operator |
| `/supervisor/login` · `/supervisor/dashboard` | Supervisor |
| `/supervisor/approvals` · `/supervisor/approvals/[actionId]` | Supervisor approval queue + exact decide UI (local substitute) |
| `/supervisor/cases/[caseId]` | Supervisor case review with opt-in approval slot |
| `/risk/login` · `/risk/dashboard` | Risk Officer |
| `/admin/login` · `/admin/dashboard` | Platform Admin |
| `/admin/users` · `/admin/users/invite` | Staff directory + invite (stub) |
| `/auth/*` | Shared auth scaffolds (verify, MFA, invitation, …) |
| `/unauthorized` | Role mismatch — authorized workspaces only |
| `/intake` | Legacy customer text intake (requires customer session) |
| `/cases/[caseId]` | Case timeline (requires customer session) |
| `/ops` | Legacy operator queue (requires operator or supervisor) |
| `/ops/cases/[caseId]/evidence` | Evidence only (no approve controls; operator-safe) |
| `/v1/capabilities` | Assembly probe |

Staff portals have **no** public sign-up. Customer registration rejects privileged fields (`roles`, `tenant_id`, `subject_refs`). Admin invite rejects `role_id=customer`.

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
| Component under test | Real web-shell + portal scaffold |
| Case API peer | Local fixture stub (+ real-peer adapter unit doubles) |
| Identity peer | Local fixture stub (+ real-peer HTTP adapter with fetch doubles) |
| Approval UI / voice | Local substitutes |
| Payment provider | N/A (UI only) |
| Model/voice live | Off |
| Money-path assembly | **Not claimed** |

Assembled live identity + case-api integration remains **unverified** until owner assembly.
