# SN-035 — Identity and access service

Standalone `identity.v1` service: users, sessions, invitations, role grants,
authz versioning, and identity audit. No money authority.

**Owned root:** `services/identity/` · **Branch:** `feat/sn-035-identity`

Contract: `sentinel.task-contracts.v1`, SHA-256
`0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.

## Scope

- Customer self-register (customer role only; privileged fields ignored/rejected;
  password length ≥ 8)
- Login / logout / me / `PATCH /v1/auth/me` profile (`display_name`,
  `preferred_language`; privilege fields rejected) / notifications inbox
  (`GET /v1/auth/notifications`, `POST .../{id}/read`) / sandbox verify-email,
  MFA challenge (numeric loopback code), forgot/reset password /
  workspaces select with hashed session tokens (multi-role login requires
  `requested_role` or returns 409)
- Platform Admin invite / grant / revoke / suspend / reactivate / list / audit
- Accept invitation (single-use; deny expired/revoked/mismatched; new password ≥ 8)
- Sandbox invite delivery: durable outbox + `GET /v1/sandbox/inbox` acceptance links
  (local demo only; set `IDENTITY_ACCEPT_LINK_BASE`, default `http://127.0.0.1:3000`)
- Sandbox auth challenges: 8+ char alphanumeric codes hashed at rest; fail-closed
  after **N=5** bad attempts per challenge; atomic consume. Plaintext OTP persists
  only when `IDENTITY_SANDBOX=true` or `SENTINEL_V1_SANDBOX=true` (column
  `auth_delivery_log.sandbox_code`). Session inbox:
  `GET /v1/auth/sandbox/latest-code?purpose=email_verify|mfa` → `{ code }` (404 when
  sandbox flag off). Password-reset inbox (no session):
  `GET /v1/auth/sandbox/password-reset-code?email=` requires
  `X-Identity-Sandbox-Token` = `IDENTITY_SANDBOX_TOKEN` (constant-time); identical
  404 for bad token / unknown email / missing challenge. Forgot always 202; when
  sandbox on, includes identical `sandbox_hint` (no email enumeration).
  `IDENTITY_EXPOSE_SANDBOX_CODES=true` still injects `sandbox_code` into 202 bodies
  for fixture/module checks only (refused in real-peers).
- `GET /v1/merchant-memberships` for merchant-teams identity peer projection
- `GET /v1/ops/team` supervisor-safe tenant roster (operator + supervisor only;
  not full `/v1/admin/users`)
- `authz_version` bump + session denial after revoke/suspend
- Seeded synthetic accounts for six human roles + cross-tenant negative

**Ruling (portal Wave 2 Team):** Supervisors must not require platform_admin.
Use `GET /v1/ops/team` for the supervisor Team page. Keep `GET /v1/admin/users`
for Platform Admin staff directory only.

**Non-goals:** ledger approvals, provider writes, Case API ownership, portal UI
(M2 admin UI / M1.3 web auth live in `apps/web`). Service principals never get
interactive logins.

## Standalone setup

```sh
cd services/identity
cp .env.example .env   # optional; fixture mode needs no peers
make check
```

`make check` runs `uv sync --frozen`, ruff, and pytest against the in-memory
store. No sibling Sentinel services, Docker, or payment credentials required.

## Run (fixture mode)

```sh
export IDENTITY_MODE=fixture
make preview
# listens on 127.0.0.1:8012
```

Default bind: `127.0.0.1:8012` (documented free port). Non-loopback bind refuses
demo seed credentials (`bind_safety`). Fixture mode loads seed principals on
serve when `IDENTITY_SEED` is truthy (default).

## Postgres seed (real-peers / portal wave 3)

```sh
export IDENTITY_DATABASE_URL=postgresql+psycopg://identity:identity@127.0.0.1:5432/identity
make seed
# prints JSON {"status":"PASS","rows":…,"notification_id":"…",…}
```

Loads `fixtures/seed_users.json` (profile fields + ≥1 notification). Challenge
OTP codes stay test-only — never written by `make seed`. Assembly harness:
`IDENTITY_DATABASE_URL` set → `make -C integration/core seed-sandbox` invokes
this hook. Live verify: `make -C integration/core verify-wave3`.

## Sandbox demo flow (auth challenges)

Product-demo path works in **real-peers + Postgres** when sandbox flags are on
(distinct from `IDENTITY_EXPOSE_SANDBOX_CODES`, which stays refused in real-peers).

```sh
export IDENTITY_MODE=real-peers
export IDENTITY_DATABASE_URL=postgresql+psycopg://identity:identity@127.0.0.1:5432/identity
export IDENTITY_SANDBOX=1          # or SENTINEL_V1_SANDBOX=1
export IDENTITY_SANDBOX_TOKEN=local-demo-token
make preview
```

1. Login → Bearer session.
2. `POST /v1/auth/verify/request` or `/v1/auth/mfa/challenge` (202, no code in body).
3. `GET /v1/auth/sandbox/latest-code?purpose=email_verify|mfa` with Bearer → `{ "code": "…" }`.
4. Confirm / verify with that code.
5. Forgot: `POST /v1/auth/password/forgot` → 202 + `sandbox_hint` (same for unknown email).
6. Reset inbox: `GET /v1/auth/sandbox/password-reset-code?email=…` with header
   `X-Identity-Sandbox-Token: $IDENTITY_SANDBOX_TOKEN` → `{ "code": "…" }` or identical 404.
7. Sandbox flag off → both GET inboxes return 404; delivery log `sandbox_code` stays NULL.

## Seeded fixture principals

See `fixtures/seed_users.json` and `contracts/principals.json`. Seed JSON has
no plaintext passwords; hashes are derived at load time from
`IDENTITY_DEMO_PASSWORD` (default `x`).

| Email | Role | Tenant |
| --- | --- | --- |
| customer@example.test | customer | tenant-demo |
| merchant@example.test | merchant | tenant-demo |
| operator@example.test | operator | tenant-demo |
| supervisor@example.test | supervisor | tenant-demo |
| risk@example.test | risk_officer | tenant-demo |
| admin@example.test | platform_admin | tenant-demo |
| admin-reviewer@example.test | platform_admin | tenant-demo |
| outsider@other.test | operator | tenant-other |

## Evidence labels

| Dimension | This module check |
| --- | --- |
| Component under test | Real `identity` implementation |
| Storage | In-memory fixture (`make check`) |
| Postgres adapter | Present; optional `@pytest.mark.postgres` |
| Payment / ledger | N/A (no money authority) |
| Portal UI / BFF | UNVERIFIED (M2 / SN-038) |
