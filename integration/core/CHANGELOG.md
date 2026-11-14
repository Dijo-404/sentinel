# SN-014 changelog

## Unreleased

### Fixed — 14 November 2026 (audit follow-up)

- `run_duplicate_payment`: always `POST /v1/admin/faults/reset` in `finally` after arming `timeout_after_accept` (covers early `FAILED_FINAL` / `PeerFault`).
- After timeout arm, first refund create must be `504` before admin confirm; `202` aborts with `PeerFault` (no credit confirm).
- Regression: `TIMEOUT_RECOVERY_MISSING` when `timeout_recovered` is false; path stays `provider-sandbox-only` (SN-009 not exercised).

### Fixed — 14 November 2026 (PR #83 review)

- `sandbox-tokens.json` unified to #84 `tok-*` → principal shape; assembly extras moved to `sandbox-assembly.json` (role→token, base_urls, journey_seeds).
- Journey order refs aligned with simulator #82 packs (`JOURNEY-*` / `DEMO-ORDER-42` / `refund-pending-1`).
- `timeout_recovered` uses actual `timeout_seen` only (no `or True`).
- Honest labels: `path=provider-sandbox-only`, `sn009_authority_exercised=false`; `SENTINEL_V1_REQUIRE_FULL_PATH=1` fails closed.

### Added — 14 November 2026

- Canonical sandbox identity matrix docs (`docs/sandbox-matrix.md`) and fixture (`fixtures/sandbox-tokens.json`): `tenant-demo` / `case-demo-42`, shared `tok-*` bearers, local port map. Refs #77 / #84.

### Added — 14 November 2026 (V1 #78)

- Real HTTP journey drivers on `HttpPeerBundle` (pending, merchant_mismatch, duplicate_payment, refund_pending); `NOT_WIRED` removed.
- Canonical sandbox matrix: `fixtures/sandbox-tokens.json`, `docs/sandbox-matrix.md` (aligned with #77 values).
- `compose.yaml` + `compose/init-databases.sql` for local multi-DB Postgres.
- `docs/sandbox-runbook.md` and `scripts/run_sandbox_journeys.sh` (nonzero on failure).
- Unit HTTP driver tests via httpx mock; optional `SENTINEL_V1_SANDBOX=1` live test.
- Real-peers reports label `payment_provider=simulator` while probes require peer `mode=real-peers`.

### Added — 13 November 2026

- Independent module ownership, architecture/interface guide, scoped agent rules and acceptance checklist.
- `sentinel-core-assembly` package producing `core-assembly.v1` with fixture and strict `real-peers` modes.
- Four journey drivers against local reference peers: pending, merchant mismatch, duplicate payment (150000-paise approval/timeout/credit recovery), refund-pending.
- Peer stub matrix under `tests/stubs/` for all seven consumed ports (`valid`, `unavailable`, `malformed`, `unauthorized_or_out_of_scope`).
- Makefile `check` target, contract snapshot, duplicate-payment fixture, and CLI self-test.
- Strict assembly rejects missing/incompatible peers and fixture evidence labeled as real; harness PASS never sets `assembled_mvp_claimed`.

### Implementation status

- Module-local fixture harness and negative strict-mode diagnostics remain covered by `make -C integration/core check`.
- HTTP journey drivers hit payment-provider only (`path=provider-sandbox-only`); they do not exercise SN-009 ledger authority.
- Full multi-service live assembly depends on peer bring-up + simulator seed packs (#82) and is exercised via the runbook/script.
- Passing fixture checks are not product release evidence. V1 sandbox PASS is not live-provider evidence.
