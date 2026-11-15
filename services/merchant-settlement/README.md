# SN-027 — merchant settlement reconciliation

**State:** implemented. Local `make check` exercises `merchant-settlement.v1` with fixture peers only.

**Owned root:** `services/merchant-settlement/`
**Branch:** `feat/sn-027-merchant-settlement`
**Produces:** `merchant-settlement.v1`
**Consumes:** `evidence.v1`, `payment-provider.v1` (local stubs under `tests/stubs/`)

Contract baseline: `sentinel.task-contracts.v1` · SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.

## Outcome

Import synthetic settlement CSV/JSON batches, match payments/orders through evidence and payment-provider ports, and own discrepancy findings:

`MISSING_PAYMENT`, `MISSING_SETTLEMENT`, `DUPLICATE_ROW`, `FEE_DIFF`, `SHORT_SETTLE`, `UNMATCHED_ORDER`.

This module never writes provider refunds or SN-009 ledger tables. Money fields are integer minor units with explicit `INR` currency. Tenant and `merchant:{ref}` subject scope are enforced from the bearer principal.

## Setup and check

Requires `uv` on PATH. No sibling Sentinel service, shared lockfile, PostgreSQL, or real payment credentials.

```sh
make -C services/merchant-settlement check
```

Syncs the module lockfile, runs ruff, then pytest (unit + HTTP + peer fail-closed). Observed mode: `fixture`.

## Run locally

```sh
cp services/merchant-settlement/.env.example services/merchant-settlement/.env
make -C services/merchant-settlement preview
# listens on MERCHANT_SETTLEMENT_HOST/PORT (default 127.0.0.1:8027)
```

Synthetic tokens are in `contracts/principals.json`. Example operator bearer: `operator-demo-token` (tenant `demo-tenant-a`, merchant `demo-merchant-1`).

## Routes

| Method | Path                                   | Auth                | Notes                                                       |
| ------ | -------------------------------------- | ------------------- | ----------------------------------------------------------- |
| GET    | `/healthz`                             | none                | liveness                                                    |
| GET    | `/readyz`                              | none                | labels `mode`                                               |
| GET    | `/v1/capabilities`                     | none                | `contract_version`, `component=merchant-settlement`, `mode` |
| POST   | `/v1/settlements/batches`              | operator/supervisor | JSON batch or `{..., csv_text}` → batch + findings          |
| GET    | `/v1/settlements/batches/{batch_id}`   | operator/supervisor | stored batch                                                |
| GET    | `/v1/settlements/findings`             | operator/supervisor | optional `batch_id`, `status`                               |
| POST   | `/v1/settlements/findings/{id}/assign` | operator/supervisor | `{assignee}` → `ASSIGNED`                                   |
| POST   | `/v1/settlements/findings/{id}/close`  | operator/supervisor | → `CLOSED`                                                  |

## Layout

```text
services/merchant-settlement/
  src/sentinel_merchant_settlement/
    domain/          # reconcile rules + types
    application/     # import + finding use cases + ports
    adapters/        # FastAPI, auth, memory store, fixture/HTTP peers
    bootstrap.py
  contracts/         # principals + typed snapshots
  fixtures/          # deterministic JSON/CSV batches
  tests/stubs/       # evidence + payment-provider cases
```

## Peer modes

- `MERCHANT_SETTLEMENT_MODE=fixture` (default): in-process stubs; readiness/capabilities label `fixture`.
- `MERCHANT_SETTLEMENT_MODE=real-peers`: HTTP adapters for evidence and payment-provider. Missing/unauthorized/malformed peers fail closed (`503`/`403`/`502`). No silent fixture fallback.

## Evidence limits

- Standalone fixture check only. Real-peer assembly against live SN-004/SN-006 remains unverified.
- No production credentials, real-money movement, or ledger writes.
- Fixture peers are not product release evidence.
