# SN-030 — merchant dispute management

Standalone `merchant-disputes.v1` service: create dispute cases, assemble transaction/order/delivery evidence packets, track deadlines, and move through `OPEN` → `EVIDENCE_PENDING` → `SUBMITTED` → `WON` / `LOST` / `WITHDRAWN`.

**Owned root:** `services/merchant-disputes/` · **Branch:** `feat/portal-wave0-1-foundation`

Contract: `sentinel.task-contracts.v1`, SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.

## HTTP list / get paths

| Method | Path                                    | Notes                                                         |
| ------ | --------------------------------------- | ------------------------------------------------------------- |
| `GET`  | `/v1/merchants/{merchant_ref}/disputes` | Tenant-scoped list; response `{"disputes":[DisputeCase,...]}` |
| `GET`  | `/v1/disputes/{dispute_id}`             | Single dispute detail                                         |

Both require `Authorization: Bearer <token>` with operator/supervisor role and merchant (and case for detail) scope.

## Standalone setup and checks

```sh
make -C services/merchant-disputes check
```

Installs only this module's `uv` dependencies (`pyproject.toml` / `uv.lock`). Fixture peers for `case-api.v1` and `evidence.v1`. Postgres proofs start a private `postgres:17-alpine` container (tmpfs) and remove it after the session. Docker required for those tests.

Preview (fixture mode):

```sh
cp services/merchant-disputes/.env.example services/merchant-disputes/.env
# export DISPUTES_TOKENS=... as in .env.example
make -C services/merchant-disputes preview
```

## Postgres + sandbox seed

```sh
export DISPUTES_DATABASE_URL=postgresql+psycopg://disputes:disputes@127.0.0.1:5432/sentinel_disputes
export SENTINEL_V1_SANDBOX=1
export DISPUTES_TENANT_ID=tenant-demo
make -C services/merchant-disputes migrate
make -C services/merchant-disputes seed
```

`make seed` inserts one `OPEN` dispute (`dispute-seed-demo-1`) for `tenant-demo` / `merchant-demo`. Non-`tenant-demo` → `SANDBOX_TENANT_REQUIRED`. Missing sandbox flag → `SANDBOX_FLAG_REQUIRED`. Non-Postgres URL → `POSTGRES_URL_REQUIRED`.

Schema: `merchant_disputes` (see [migrations/README.md](migrations/README.md)).

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

Set `DISPUTES_MODE=real-peers` plus `CASE_API_*` and `EVIDENCE_*` URLs/tokens and `DISPUTES_DATABASE_URL` (PostgreSQL or sqlite). Missing or failing peers/DB surface as errors; fixture peers are never substituted. Assembly against live SN-006/007 is **unverified** until owner-run.
