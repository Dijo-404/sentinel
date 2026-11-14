# SN-034 / SN-039 — merchant team and role management

Standalone `merchant-teams.v1` service: merchant-scoped staff accounts, roles,
advisory `approval_limit_minor`, append-only activity timeline, and
identity-authoritative membership projection (SN-039).

**Owned root:** `services/merchant-teams/` · **Branch:** `feat/sn-039-merchant-teams`

Contract: `sentinel.task-contracts.v1`, SHA-256
`0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.

## Scope

- Create / update / deactivate staff under a tenant + `merchant_ref`
- Assign merchant subroles only (`viewer`, `operator`, `approver`, `admin`)
- Store advisory approval limits (integer minor units + currency)
- Append-only `StaffActivity` timeline
- Consume `case-api.v1` when recording `CASE_*` activity (local stubs for checks)
- Project `identity.v1` merchant memberships into the local store
  (`POST /v1/staff/sync`); Platform Admin / identity owns grants
- `GET /v1/merchant/team` auto-syncs when identity is configured and labels
  the list as a projection (`source`)
- Sync deactivates local staff absent from identity (revoke)
- Optional PostgreSQL durable store + sandbox seed for portal real-peers

**Non-goals:** this module never creates approvals or reservations, never writes
SN-009 ledger tables, and never calls payment providers. Advisory limits cannot
authorize money. `POST /v1/staff/{id}/authorize` always returns 403. This module
is not a second platform role authority. With `IDENTITY_BASE_URL` in real-peers,
local create/update role mutations are rejected (projection-only).

## List APIs (portal Team page)

Prefer the projection surface for merchant portal Team:

| Method | Path | Response |
| --- | --- | --- |
| `GET` | `/v1/merchant/team?merchant_ref=merchant-demo-1` | `{ "staff": MerchantStaff[], "source": "identity_projection" \| "local_projection" }` |
| `GET` | `/v1/staff?merchant_ref=merchant-demo-1` | `{ "staff": MerchantStaff[] }` |

Auth: `Authorization: Bearer <token>` from `MERCHANT_TEAMS_TOKENS`. Operator /
supervisor / sandbox-admin with merchant scope. Empty merchant list is honest
`[]` from the store — never invent client-side demo rows.

When `IDENTITY_BASE_URL` is set, `GET /v1/merchant/team` refreshes from identity
first (`source=identity_projection`). Without identity, seeded/local rows use
`source=local_projection`.

## Standalone setup

```sh
cd services/merchant-teams
cp .env.example .env   # optional; fixture mode needs no peers
make check
```

`make check` runs `uv sync --frozen`, ruff, and pytest. Fixture tests use
in-memory storage and `tests/stubs/`. Postgres proofs need Docker and are marked
`postgres`.

## Postgres + sandbox seed

```sh
export MERCHANT_TEAMS_DATABASE_URL='postgresql+psycopg://postgres:postgres@127.0.0.1:5432/merchant_teams'
make seed
# {"evidence_label":"synthetic_seed","merchant_ref":"merchant-demo-1","staff_id":"staff-demo-1","status":"PASS","tenant_id":"tenant-demo"}
```

Seed migrates schema `merchant_teams`, upserts `staff-demo-1` for
`tenant-demo` / `merchant-demo-1` from `fixtures/staff_demo.json` (synthetic),
and appends demo activity when missing. Idempotent.

real-peers requires `MERCHANT_TEAMS_DATABASE_URL` (or an injected durable store).

## Run (fixture mode)

```sh
export MERCHANT_TEAMS_MODE=fixture
export MERCHANT_TEAMS_TOKENS='operator-token=op-1|tenant-demo|operator|merchant-demo-1|case-demo-42'
make preview
# listens on 127.0.0.1:8034
```

## Real-peer mode

Set `MERCHANT_TEAMS_MODE=real-peers`, `CASE_API_BASE_URL`, `CASE_API_TOKEN`, and
`MERCHANT_TEAMS_DATABASE_URL`. Unavailable, unauthorized, or malformed case-api
responses fail closed with no fixture fallback.

Optional: set `IDENTITY_BASE_URL` and `IDENTITY_TOKEN` to enable membership
sync against identity.v1 (`GET /v1/merchant-memberships`). When configured,
identity failures fail closed, sync revokes absent locals, team list
auto-syncs, and local membership writes are projection-only. See
`contracts/real-peer-compat.md`.

## Evidence labels

| Dimension | This module check |
| --- | --- |
| Component under test | Real `merchant-teams` implementation |
| case-api peer | Local stub (`fixture`) |
| identity peer | Local stub (`fixture`); optional real-peer when `IDENTITY_BASE_URL` set |
| Persistence | In-memory (`fixture`); PostgreSQL when `MERCHANT_TEAMS_DATABASE_URL` set |
| Sandbox seed | Synthetic (`make seed` → `evidence_label=synthetic_seed`) |
| Payment provider | N/A (no provider writes) |
| Assembly / live peers | UNVERIFIED |
