# observability — telemetry signal ingest/query

Independent `observability.v1` HTTP+DB peer: sandbox ingest and admin list of
sampled telemetry signals/spans. Wire fields align with `packages/telemetry`
`RecordedSpan` (`name`, `attributes`, `events`). **Never financial audit.**

**Owned root:** `services/observability/` · **Default port:** `8033`

Contract: `sentinel.task-contracts.v1`, SHA-256
`0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.
Typed snapshot: [contracts/observability.v1.json](contracts/observability.v1.json).
Compatibility: [contracts/COMPATIBILITY.md](contracts/COMPATIBILITY.md).

## Routes

| Method | Path          | Roles                         | Response                               |
| ------ | ------------- | ----------------------------- | -------------------------------------- |
| `POST` | `/v1/ingest`  | platform_admin, sandbox-admin | `{ accepted, financial_audit: false }` |
| `GET`  | `/v1/signals` | platform_admin, sandbox-admin | `{ signals, financial_audit: false }`  |
| `GET`  | `/v1/spans`   | platform_admin, sandbox-admin | `{ spans, financial_audit: false }`    |

Also: `/healthz`, `/readyz`, `/v1/capabilities` (`mode: fixture|real-peers`,
`financial_audit: false`, `financial_authority: false`).

Ingest accepts either `signals[]` (full signal objects) or `spans[]`
(telemetry `RecordedSpan` shape). List spans projects `name`/`attributes`/`events`.

## Standalone setup and checks

Requires Python 3.11+, [uv](https://docs.astral.sh/uv/), GNU Make, Docker (Postgres
integration tests). From this directory:

```sh
make setup
make check
```

Or from the repository root:

```sh
make -C services/observability check
```

## Configuration

See [.env.example](.env.example).

```sh
export OBSERVABILITY_MODE=fixture
export OBSERVABILITY_TOKENS='admin-token=admin-1|tenant-demo|platform_admin'
make preview
```

`OBSERVABILITY_MODE=real-peers` requires `OBSERVABILITY_DATABASE_URL`. No silent
memory/fixture fallback. Missing DB → `503` / `PEER_UNAVAILABLE`.

### Seed (sandbox)

Requires `OBSERVABILITY_DATABASE_URL`. Writes one synthetic span for `tenant-demo`:

```sh
export OBSERVABILITY_DATABASE_URL=postgresql+psycopg://...
make seed
```
