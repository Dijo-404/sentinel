# observability.v1 compatibility

Baseline contract: `sentinel.task-contracts.v1`  
SHA-256: `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`

Aligns wire fields with `packages/telemetry` `RecordedSpan`
(`name`, `attributes`, `events`). This peer is **sampled telemetry ingest/query
only**. It never stores, replaces, or claims financial audit (ledger-owned,
unsampled).

## Failure modes

| Condition | Code | HTTP |
| --- | --- | --- |
| Missing/unknown bearer | `FORBIDDEN` | 403 |
| Role not platform_admin/sandbox-admin | `FORBIDDEN` | 403 |
| real-peers without DB | `PEER_UNAVAILABLE` | 503 |
| Postgres unavailable | `PEER_UNAVAILABLE` | 503 |
| Malformed ingest body | `INVALID_INPUT` | 422 |

No silent fixture fallback in `OBSERVABILITY_MODE=real-peers`.
