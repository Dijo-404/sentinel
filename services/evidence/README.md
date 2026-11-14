# SN-006 — Evidence and reconciliation service

Independent `evidence.v1` HTTP service: collect scoped read-only payment-provider facts, retain original digest/provenance/freshness, and emit deterministic reconciliation codes. Owns local storage/migrations and payment-provider doubles. Does **not** import `services/simulator`.

**Owned root:** `services/evidence/` · **Branch:** `feat/sn-006-evidence`

Contract: `sentinel.task-contracts.v1`, SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`. Typed snapshot: [contracts/evidence.v1.json](contracts/evidence.v1.json).

## Routes

| Method | Path | Roles | Response |
| --- | --- | --- | --- |
| `POST` | `/v1/evidence/collect` | workflow, verifier | `EvidenceBundle` |
| `GET` | `/v1/cases/{case_id}/evidence` | workflow, verifier, operator, supervisor | `EvidenceBundle` |

Also: `/healthz`, `/readyz`, `/v1/capabilities` (`mode: fixture|real-peers`).

## Standalone setup and checks

Requires Python 3.11+, [uv](https://docs.astral.sh/uv/), GNU Make, Docker (PostgreSQL acceptance). From this directory:

```sh
make setup
make check
```

Or from the repository root:

```sh
make -C services/evidence check
make check
```

`make check` runs Ruff lint/format and pytest. PostgreSQL tests start a disposable `postgres:17-alpine` container on `127.0.0.1`; they never use a shared Sentinel database.

## Local peer doubles

`tests/stubs/` implements `payment-provider.v1` cases:

| Module | Behavior |
| --- | --- |
| `valid` | Two distinct captured payments, under-fulfilled order, merchant-confirmed duplicate |
| order suffix `#equal` | Equal amounts without merchant confirmation → `EQUAL_AMOUNTS_INSUFFICIENT` (never `DUPLICATE_PAYMENT`) |
| order suffix `#stale` | Expired snapshot → `UNVERIFIED` + `STALE_PROVIDER_SNAPSHOT` |
| order suffix `#conflict` | Contradictory payment records → `CONFLICTING` |
| `unavailable` / `#unavailable` | `PEER_UNAVAILABLE` (503) |
| `malformed` / `#malformed` | `PEER_MALFORMED` (502) |
| `unauthorized_or_out_of_scope` / `#unauthorized` | `PEER_UNAUTHORIZED` (403) |

Authorized case `order_reference` may be `{subject_ref}/{customer_order_id}` (or `:`). Collect derives the bare provider key for payment-provider calls and keeps the authorized value on the collect request/store row. Fixture scenario markers use `#` so they never collide with subject boundaries.

**Duplication rule:** `DUPLICATE_PAYMENT` requires `DISTINCT_TRANSACTION_REFS`, `MERCHANT_CONFIRMED_DUPLICATE`, and `ORDER_UNDERFULFILLED`. Equal `amount_minor` alone is never enough.

## Configuration

See [.env.example](.env.example). `EVIDENCE_MODE=fixture` uses in-process stubs. `EVIDENCE_MODE=real-peers` requires `PAYMENT_PROVIDER_BASE_URL` and `PAYMENT_PROVIDER_TOKEN` and **fails closed** on unavailable/malformed/unauthorized peers — no silent fixture fallback.

```sh
# fixture mode allows in-process memory store without DATABASE_URL
export EVIDENCE_MODE=fixture
export EVIDENCE_TOKENS='tok-workflow=svc-workflow|tenant-demo|workflow|subject-demo-42|case-demo-42'
make preview
```

Real/default path requires Postgres (`DATABASE_URL`). Set `SENTINEL_EVIDENCE_ALLOW_MEMORY=1` only for explicit local doubles. Empty `case_ids` deny; `*` allows all cases.

With PostgreSQL:

```sh
export DATABASE_URL=postgresql+psycopg://...
uv run --frozen sentinel-evidence migrate
uv run --frozen sentinel-evidence serve --port 8006
```

## Compatibility checklist

- [x] Task-local contract snapshot, fixtures, and peer stubs
- [x] Collect/list routes with bearer principal map and case/subject scope
- [x] Digest = SHA-256 of retained original UTF-8 snapshot bytes
- [x] Explicit states for valid/stale/conflicting/unauthorized/unavailable
- [x] Equal amounts alone never prove duplication
- [x] Real-peer HTTP adapter fail-closed (no fixture fallback)
- [x] Own PostgreSQL schema/tables for durable evidence retention
- [ ] Assembled product wiring against a live SN-004 simulator (owner assembly)

## Evidence status

Standalone fixture + private PostgreSQL checks only. No running sibling services, live payment credentials, or product/pilot release claim.
