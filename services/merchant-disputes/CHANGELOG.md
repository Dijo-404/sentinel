# SN-030 changelog

## Unreleased

### Fixed

- Real-peers bootstrap refuses default `MemoryDisputeStore`; requires an injected
  durable store so worker processes cannot wipe or split state.

### Added

- Independent `merchant-disputes.v1` HTTP service with dispute lifecycle, evidence packet assembly, and deadline tracking.
- Fixture and real-peer adapters for `case-api.v1` and `evidence.v1`; local stubs for valid/unavailable/malformed/unauthorized cases.
- Acceptance tests for lifecycle, evidence gate, deadline overdue, and fail-closed peer/auth behavior.
- Module `make check`, `.env.example`, contract snapshot, and compatibility checklist.
- Contract pin: `sentinel.task-contracts.v1` SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.
