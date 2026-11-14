# SN-036 changelog

## Unreleased

### Changed

- `GET /v1/risk/cases/{case_id}/blocks` accepts `workflow` service principals
  (in addition to `risk_officer`) so workflow can enforce holds fail-closed.

### Fixed

- Restriction decisions require `expected_revision`; store compare-and-swap
  claims the revision before CLEAR resume emit so concurrent CLEAR cannot
  double-emit. Stale revision returns conflict. Emit failure leaves the block
  active (claimed revision) and CLEAR retryable with the new revision.
- CLEAR persists unblocked restriction only after successful workflow resume emit;
  emit failure leaves the block active and CLEAR retryable.
- Ledger approval deny surfaces return `LEDGER_APPROVAL_FORBIDDEN` for any
  authenticated caller (not only `risk_officer`).

### Added

- Independent `risk.v1` HTTP service: investigations, findings, authorized restrictions.
- Fixture memory store and optional PostgreSQL adapter (`RISK_DATABASE_URL`).
- Fixture/real-peer adapters for case-api and workflow resume; local stubs including ledger deny.
- AUTH-21 deny surfaces for ledger approval attempts (`LEDGER_APPROVAL_FORBIDDEN`).
- FLOW-10/11 coverage: active restriction blocks flag; clearance resumes workflow without money approval.
- Module `make check`, `.env.example`, contract snapshot, compatibility checklist.
- Default preview listen `127.0.0.1:8013`.
- Contract pin: `sentinel.task-contracts.v1` SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.
