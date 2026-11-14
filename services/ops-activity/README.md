# ops-activity — operator activity feed

Independent `ops-activity.v1` HTTP service: tenant-scoped activity items newest
first (max 50). Local Postgres rows for sandbox/real-peers. No ledger writes.
No case-api projection yet (documented sync stub).

**Owned root:** `services/ops-activity/` · **Default port:** `8029`

Contract: `sentinel.task-contracts.v1`, SHA-256
`0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.
Typed snapshot: [contracts/ops-activity.v1.json](contracts/ops-activity.v1.json).
Compatibility: [contracts/COMPATIBILITY.md](contracts/COMPATIBILITY.md).

## Routes

| Method | Path | Roles | Response |
| --- | --- | --- | --- |
| `GET` | `/v1/activity` | operator, supervisor | `{ items: ActivityItem[] }` |

Also: `/healthz`, `/readyz`, `/v1/capabilities` (`mode: fixture|real-peers`,
`financial_authority: false`).

`ActivityItem`: `activity_id`, `kind`, `summary`, `occurred_at`, optional `case_id`.

## Standalone setup and checks

Requires Python 3.11+, [uv](https://docs.astral.sh/uv/), GNU Make, Docker (Postgres
integration tests). From this directory:

```sh
make setup
make check
```

Or from the repository root:

```sh
make -C services/ops-activity check
```

## Configuration

See [.env.example](.env.example).

```sh
export OPS_ACTIVITY_MODE=fixture
export OPS_ACTIVITY_TOKENS='operator-token=op-1|tenant-demo|operator;supervisor-token=sup-1|tenant-demo|supervisor'
make preview
```

`OPS_ACTIVITY_MODE=real-peers` requires `OPS_ACTIVITY_DATABASE_URL`. No silent
memory/fixture fallback. Missing DB → `503` / `PEER_UNAVAILABLE`.

### Seed (sandbox)

Requires `OPS_ACTIVITY_DATABASE_URL`. Writes one synthetic row for `tenant-demo` /
`case-demo-42` only:

```sh
export OPS_ACTIVITY_DATABASE_URL=postgresql+psycopg://...
make seed
```

## Sync stub

Feed is **local seed/insert rows only**. Case-api outbox projection is out of
scope for this module cut; see `contracts/COMPATIBILITY.md`.
