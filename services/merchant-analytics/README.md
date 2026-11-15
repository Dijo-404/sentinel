# SN-032 — merchant analytics aggregates

Independent `merchant-analytics.v1` HTTP service: merchant-scoped read-only aggregates
(exception rate, unresolved minor units, refund aging buckets, median handling time,
top causes). Fixture mode aggregates from `case-api.v1` / `evidence.v1` stubs. Real-peers
prefer Postgres snapshots (`MERCHANT_ANALYTICS_DATABASE_URL`) so portal rows are seeded
DB data, not invented client fixtures. No peer mutations. No ledger writes. No real payments.

**Owned root:** `services/merchant-analytics/` · **Branch:** `feat/sn-032-merchant-analytics`

Contract: `sentinel.task-contracts.v1`, SHA-256
`0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.
Typed snapshot: [contracts/merchant-analytics.v1.json](contracts/merchant-analytics.v1.json).
Expected fixture metrics: [contracts/expected-metrics.json](contracts/expected-metrics.json).

## Routes

| Method | Path                                                           | Roles                | Response          |
| ------ | -------------------------------------------------------------- | -------------------- | ----------------- |
| `GET`  | `/v1/merchants/{merchant_ref}/metrics?window_start&window_end` | operator, supervisor | `MerchantMetrics` |

Also: `/healthz`, `/readyz`, `/v1/capabilities` (`mode: fixture|real-peers`).
`POST`/`PUT`/`PATCH`/`DELETE` on metrics return 405.

## Standalone setup and checks

Requires Python 3.11+, [uv](https://docs.astral.sh/uv/), GNU Make. From this directory:

```sh
make setup
make check
```

Or from the repository root:

```sh
make -C services/merchant-analytics check
make check
```

`make check` runs Ruff lint/format and pytest (including disposable Docker Postgres
for snapshot proofs). Checks use only this module, local fixtures under `fixtures/`,
and stubs under `tests/stubs/`. No sibling Sentinel services or payment credentials.

## Local peer doubles

| Port          | Location                | Behaviors                                                   |
| ------------- | ----------------------- | ----------------------------------------------------------- |
| `case-api.v1` | `tests/stubs/case_api/` | valid, unavailable, malformed, unauthorized_or_out_of_scope |
| `evidence.v1` | `tests/stubs/evidence/` | valid, unavailable, malformed, unauthorized_or_out_of_scope |

Deterministic fixture window `2026-11-01T00:00:00Z`–`2026-11-14T00:00:00Z` for
`merchant-demo-1` yields `exception_rate=0.4000`, `unresolved_minor=100000`, aging
buckets `{0-24h:1,1-3d:1,3-7d:1,7d+:0}`, `median_handling_seconds=2700`, and ranked
`top_causes`.

## Configuration

See [.env.example](.env.example).

```sh
export MERCHANT_ANALYTICS_MODE=fixture
export MERCHANT_ANALYTICS_TOKENS='operator-token=op-1|tenant-demo|operator|subj-demo-1|*|merchant-demo-1'
make preview
```

`MERCHANT_ANALYTICS_MODE=real-peers` with `MERCHANT_ANALYTICS_DATABASE_URL` serves
metrics from `merchant_analytics.merchant_metrics_snapshots` only (no live peer invent,
no fixture fallback). Missing snapshot → `404` / `SNAPSHOT_NOT_FOUND`. DB down → `503` /
`PEER_UNAVAILABLE`. Without a database URL, real-peers still requires `CASE_API_*` and
`EVIDENCE_*` and fails closed on bad peers. Real-peer assembly remains unverified until
owner-run integration.

### Seed (sandbox)

Requires `MERCHANT_ANALYTICS_DATABASE_URL`. Refuses non-`tenant-demo` /
non-`merchant-demo-1` payloads:

```sh
export MERCHANT_ANALYTICS_DATABASE_URL=postgresql+psycopg://...
make seed
```

Writes one row for the matrix window in `contracts/expected-metrics.json`.

## Compatibility checklist

- [x] Task-local contract snapshot, fixtures, and peer stubs
- [x] Read-only metrics route with bearer principal + merchant scope
- [x] Integer minor units; exception rate as fixed decimal string
- [x] Unauthorized merchant scope and unavailable peers fail closed
- [x] Real-peer HTTP adapters never fall back to fixtures
- [x] Postgres snapshot store + `make seed` for portal real-peers
