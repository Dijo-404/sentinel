# SN-034 — merchant team and role management

Standalone `merchant-teams.v1` service: merchant-scoped staff accounts, roles,
advisory `approval_limit_minor`, and an append-only activity timeline.

**Owned root:** `services/merchant-teams/` · **Branch:** `feat/sn-034-merchant-teams`

Contract: `sentinel.task-contracts.v1`, SHA-256
`0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.

## Scope

- Create / update / deactivate staff under a tenant + `merchant_ref`
- Assign staff roles (`viewer`, `operator`, `approver`, `admin`)
- Store advisory approval limits (integer minor units + currency)
- Append-only `StaffActivity` timeline
- Consume `case-api.v1` when recording `CASE_*` activity (local stubs for checks)

**Non-goals:** this module never creates approvals or reservations, never writes
SN-009 ledger tables, and never calls payment providers. Advisory limits cannot
authorize money. `POST /v1/staff/{id}/authorize` always returns 403.

## Standalone setup

```sh
cd services/merchant-teams
cp .env.example .env   # optional; fixture mode needs no peers
make check
```

`make check` runs `uv sync --frozen`, ruff, and pytest. It uses only this
module, in-memory storage, and `tests/stubs/` case-api doubles. No sibling
Sentinel services, Docker, or payment credentials are required.

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
fixture fallback. See `contracts/real-peer-compat.md`.

## Evidence labels

| Dimension | This module check |
| --- | --- |
| Component under test | Real `merchant-teams` implementation |
| case-api peer | Local stub (`fixture`) |
| Payment provider | N/A (no provider writes) |
| Assembly / live case-api | UNVERIFIED |
