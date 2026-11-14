# SN-033 changelog

## Unreleased
- Refuse non-loopback HTTP bind while demo/sandbox bearer tokens remain configured.

### Added

- `merchant-comms.v1` library and HTTP adapter: EN/TA/HI `CommsDraft` generation, operator approval gate, simulated delivery history.
- Required `case-api.v1` and optional `indic-context.v1` ports with fixture stubs and real-peer HTTP adapters that fail closed (no silent fixture fallback on required peers).
- Deterministic template fallback labeled `[fake]` when optional Indic context is missing or unavailable.
- Local `make check` (uv + ruff + pytest), configuration example, contract snapshots and compatibility checklist.
- Contract pin: `sentinel.task-contracts.v1` SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.

### Notes

- Independent module ownership scaffold and scoped agent rules retained from bootstrap.
