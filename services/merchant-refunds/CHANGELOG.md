# SN-029 changelog

## Unreleased
- Refuse non-loopback HTTP bind while demo/sandbox bearer tokens remain configured.

### Fixed

- Real-peers bootstrap refuses default `MemoryRequestStore`; requires an injected
  durable store so worker processes cannot wipe or split state.

### Added

- Installable `merchant-refunds.v1` HTTP service with draft/submit/decision/sync
  lifecycle for `MerchantRefundRequest`.
- Domain rules: integer money, fail-closed peer errors, ledger-only `action_id`,
  pending ≠ verified credit.
- Local stubs for `case-api.v1`, `policy.v1`, `action-ledger.v1`, `evidence.v1`
  (valid / unavailable / malformed / unauthorized_or_out_of_scope).
- Real-peer HTTP adapters with no fixture fallback; compatibility checklist.
- Contract snapshots, digest fixture, demo request fixture, `make check`.
- Contract pin: `sentinel.task-contracts.v1` SHA-256
  `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.
