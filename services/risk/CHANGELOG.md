# SN-036 changelog

## Unreleased

### Added

- Independent `risk.v1` HTTP service: investigations, findings, authorized restrictions.
- Fixture memory store and optional PostgreSQL adapter (`RISK_DATABASE_URL`).
- Fixture/real-peer adapters for case-api and workflow resume; local stubs including ledger deny.
- AUTH-21 deny surfaces for ledger approval attempts (`LEDGER_APPROVAL_FORBIDDEN`).
- FLOW-10/11 coverage: active restriction blocks flag; clearance resumes workflow without money approval.
- Module `make check`, `.env.example`, contract snapshot, compatibility checklist.
- Default preview listen `127.0.0.1:8013`.
- Contract pin: `sentinel.task-contracts.v1` SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.
