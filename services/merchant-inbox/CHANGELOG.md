# SN-028 changelog

## Unreleased
- Refuse non-loopback HTTP bind while demo/sandbox bearer tokens remain configured.

### Added

- Independent `merchant-inbox.v1` service: list/filter, assign, notes, escalate for synthetic PAID_UNFULFILLED, UNMATCHED_PAYMENT, and PENDING_REFUND items.
- Escalation invariant: status becomes `ESCALATED` with `resolved=false`; never treated as verified financial closure or `CLOSED`.
- Local case-api.v1 and evidence.v1 stubs (valid / unavailable / malformed / unauthorized) and real-peer HTTP adapters that fail closed.
- Module packaging (`pyproject.toml`, `uv.lock`, `Makefile`), contract snapshots, acceptance tests, and `make check`.
- Contract pin: `sentinel.task-contracts.v1` SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.
