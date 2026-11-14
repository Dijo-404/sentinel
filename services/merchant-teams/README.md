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

**Non-goals:** this module never creates approvals or reservations, never writes
SN-009 ledger tables, and never calls payment providers. Advisory limits cannot
authorize money. `POST /v1/staff/{id}/authorize` always returns 403. This module
is not a second platform role authority.

## Standalone setup

```sh
cd services/merchant-teams
cp .env.example .env   # optional; fixture mode needs no peers
make check
```

`make check` runs `uv sync --frozen`, ruff, and pytest. It uses only this
module, in-memory storage, and `tests/stubs/` doubles (case-api + identity).
No sibling Sentinel services, Docker, or payment credentials are required.

## Run (fixture mode)

```sh
export MERCHANT_TEAMS_MODE=fixture
export MERCHANT_TEAMS_TOKENS='operator-token=op-1|tenant-demo|operator|merchant-demo-1|case-demo-42'
make preview
# listens on 127.0.0.1:8034
```

## Real-peer mode

Set `MERCHANT_TEAMS_MODE=real-peers`, `CASE_API_BASE_URL`, and `CASE_API_TOKEN`.
Unavailable, unauthorized, or malformed case-api responses fail closed with no
fixture fallback.

Optional: set `IDENTITY_BASE_URL` and `IDENTITY_TOKEN` to enable membership
sync against identity.v1 (`GET /v1/merchant-memberships`). When configured,
identity failures fail closed. See `contracts/real-peer-compat.md`.

## Evidence labels

| Dimension | This module check |
| --- | --- |
| Component under test | Real `merchant-teams` implementation |
| case-api peer | Local stub (`fixture`) |
| identity peer | Local stub (`fixture`); optional real-peer when `IDENTITY_BASE_URL` set |
| Payment provider | N/A (no provider writes) |
| Assembly / live peers | UNVERIFIED |
