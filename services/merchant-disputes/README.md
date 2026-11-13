# SN-030 — merchant dispute management

Standalone `merchant-disputes.v1` service: create dispute cases, assemble transaction/order/delivery evidence packets, track deadlines, and move through `OPEN` → `EVIDENCE_PENDING` → `SUBMITTED` → `WON` / `LOST` / `WITHDRAWN`.

**Owned root:** `services/merchant-disputes/` · **Branch:** `feat/sn-030-merchant-disputes`

Contract: `sentinel.task-contracts.v1`, SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.

## Standalone setup and checks

```sh
make -C services/merchant-disputes check
```

Installs only this module's `uv` dependencies (`pyproject.toml` / `uv.lock`). Uses in-process fixture peers for `case-api.v1` and `evidence.v1`. No sibling Sentinel services, no PostgreSQL, no real payment credentials.

Preview (fixture mode):

```sh
cp services/merchant-disputes/.env.example services/merchant-disputes/.env
# export DISPUTES_TOKENS=... as in .env.example
make -C services/merchant-disputes preview
```

## Scope

- Owns dispute state and evidence packet IDs only.
- Consumes `case-api.v1` (case lookup) and `evidence.v1` (collect) via injected ports.
- Submission blocked until packets contain `PAYMENT`, `ORDER`, and `DELIVERY` kinds.
- Past `deadline_at` blocks submission (`DEADLINE_PASSED`).
- Unauthorized merchant/case scope and unavailable peers fail closed.
- Does **not** edit SN-009 ledger tables or mint refunds.

## Local stubs

Under `tests/stubs/case_api/` and `tests/stubs/evidence/`: `valid`, `unavailable`, `malformed`, `unauthorized_or_out_of_scope`.

## Real-peer mode

Set `DISPUTES_MODE=real-peers` plus `CASE_API_*` and `EVIDENCE_*` URLs/tokens. Missing or failing peers surface as errors; fixture peers are never substituted. Assembly against live SN-006/007 is **unverified** until owner-run.
