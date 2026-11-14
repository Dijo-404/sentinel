# SN-012 changelog

## Unreleased

### Added — 14 November 2026

- `GET /v1/capabilities` assembly probe: `{ contract_version, component: "web-shell", port: "web-shell.v1", mode }` from `NEXT_PUBLIC_SHELL_MODE` (Refs #76).

### Added — 13 November 2026

- Next.js web shell (`web-shell.v1`): text intake, case timeline, operator queue, evidence workspace.
- Domain masking for subject/transaction/provider/order refs; exact pending/provider/credit/escalation labels.
- Local stubs for `case-api.v1`, `approval-ui.v1`, `voice.v1` under `tests/stubs/` (valid, unavailable, malformed, unauthorized_or_out_of_scope).
- Real-peer case-api adapter that surfaces failures without fixture fallback.
- Approval and voice component slots with local substitutes; voice disabled by default.
- Module `Makefile` (`make check`), `.env.example`, contract snapshots/fixtures, Vitest browser-state checks.

### Implementation status

- Standalone fixture checks implemented. Assembled SN-007/SN-013/SN-017 real-peer evidence unverified.
- Contract baseline SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.
