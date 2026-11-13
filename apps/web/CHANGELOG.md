# SN-012 changelog

## Unreleased

### Added — 13 November 2026

- Next.js web shell (`web-shell.v1`): text intake, case timeline, operator queue, evidence workspace.
- Domain masking for subject/transaction/provider/order refs; exact pending/provider/credit/escalation labels.
- Local stubs for `case-api.v1`, `approval-ui.v1`, `voice.v1` under `tests/stubs/` (valid, unavailable, malformed, unauthorized_or_out_of_scope).
- Real-peer case-api adapter that surfaces failures without fixture fallback.
- Approval and voice component slots with local substitutes; voice disabled by default.
- Module `Makefile` (`make check`), `.env.example`, contract snapshots/fixtures, Vitest browser-state checks.

### Implementation status

- Standalone fixture checks implemented. Assembled SN-007/SN-013/SN-017 real-peer evidence unverified.
- Contract baseline SHA-256 `0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa`.
