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
- Sandbox auth challenges: loopback delivery log; codes never in public JSON unless
  `IDENTITY_EXPOSE_SANDBOX_CODES=true` (module checks only; blocked in real-peers).
  Forgot password always 202 (no email enumeration).
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
demo seed credentials (`bind_safety`).

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
