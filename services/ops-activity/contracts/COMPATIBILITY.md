# ops-activity.v1 compatibility

Baseline contract: `sentinel.task-contracts.v1`  
SHA-256: `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`

## Sync stub

`GET /v1/activity` serves **local** `ops_activity.activity_items` rows only.

Case-api outbox / event projection is **not** wired in this wave. Seed inserts
synthetic sandbox rows for `tenant-demo`. A future projection job may append
rows with the same wire shape; consumers must tolerate additive kinds.

## Failure modes

| Condition | Code | HTTP |
| --- | --- | --- |
| Missing/unknown bearer | `FORBIDDEN` | 403 |
| Role not operator/supervisor | `FORBIDDEN` | 403 |
| real-peers without DB | `PEER_UNAVAILABLE` | 503 |
| Postgres unavailable | `PEER_UNAVAILABLE` | 503 |

No silent fixture fallback in `OPS_ACTIVITY_MODE=real-peers`.
