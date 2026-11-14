# SN-031 changelog

## Unreleased
- Refuse non-loopback HTTP bind while demo/sandbox bearer tokens remain configured.

### Fixed

- Real-peers bootstrap refuses default `MemorySlaStore`; requires
  `MERCHANT_SLA_DATABASE_URL` (sqlite) or an injected durable store so worker
  processes cannot wipe or split state.

### Added

- Independent `merchant-sla.v1` HTTP service: SLA policies, task assignment, overdue highlighting via injectable/virtual clock, follow-up scheduling.
- Escalation sets task `ESCALATED` and case `ESCALATED`; never `DONE` and never financial `VERIFIED_RESOLVED`. Explicit `complete` is the non-financial DONE transition.
- Local `case-api.v1` stubs (`valid`, `unavailable`, `malformed`, `unauthorized_or_out_of_scope`) plus real-peer HTTP adapter that fails closed with no fixture fallback.
- Module manifest/lockfile, `.env.example`, `make check` / `preview`, contract snapshots, compatibility checklist.
- Contract pin: `sentinel.task-contracts.v1` SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.
