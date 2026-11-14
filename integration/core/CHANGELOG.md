# SN-014 changelog

## Unreleased

### Added — 15 November 2026 (case-api ops seed hook)

- `seed_sandbox` invokes `make -C apps/api seed` when `SENTINEL_API_DATABASE_URL`
  is set (ESCALATED + HISTORY ops surface rows for wave 2).

### Added — 15 November 2026 (portal wave 0–1 verify)

- `verify_wave0_1` + `scripts/verify_wave0_1.sh` / `make verify-wave0-1` /
  `sentinel-core-assembly verify-wave0-1`: HTTP 200 + seeded JSON for analytics
  metrics, disputes list, risk investigations (fails closed without seed).
- `seed_sandbox` invokes `make seed` for merchant-analytics / merchant-disputes /
  risk when `*_DATABASE_URL` is set; otherwise SKIPPED with run-order docs.
- README curl checklist + Wave 0–1 run order; matrix ports 8030 / 8032.

### Added — 15 November 2026 (portal wave 0 seed gate)

- `seed_sandbox` adapter + `sentinel-core-assembly seed-sandbox` CLI / `make seed-sandbox`.
- Refuses non-`tenant-demo` (`SANDBOX_TENANT_REQUIRED`) and missing `SENTINEL_V1_SANDBOX`
  (`SANDBOX_FLAG_REQUIRED`). Pending peer hooks report `SKIPPED` until module seeds land.

### Added — 14 November 2026 (finding #8 browser-to-credit)

- Authority journeys `browser_to_credit` and `duplicate_approval_deny`: intake →
  proposal → approval → reservation → dispatcher-role claim → verifier → customer
  closure, plus conflicting-approval deny (no refund side effect).
- Fixture doubles set `path=browser-to-credit-fixture` and
  `sn009_authority_exercised=true` when those journeys pass; `assembled_mvp_claimed`
  stays false.
- Real-peer HTTP drivers gated by `SENTINEL_V1_AUTHORITY_PATH=1`; on success
  `path=browser-to-credit`, `sn009_authority_exercised=true`.
- Default real-peers still provider journeys only (`path=provider-sandbox-only`).
- `SENTINEL_V1_REQUIRE_FULL_PATH=1` requires `path=browser-to-credit` after journeys.
- Runbook / matrix / seeds / contract snapshot updated for honesty labels.

### Fixed — 14 November 2026 (RBAC fixture role catalog)

- `_STAFF_ROLES` aligned with identity `STAFF_INVITABLE_ROLES` (dropped legacy `admin` alias).
- Regression: fixture invite of `role_id=admin` denied; set equality asserted in tests.

### Added — 14 November 2026 (SN-041 Refs #104)

- Identity (8012) and risk (8013) ports/tokens in sandbox matrix + assembly fixtures;
  compose Postgres users/DBs for identity and risk.
- Fixture RBAC probes (`path=rbac-fixture`): AUTH-01 staff-role register denied,
  platform-admin staff invite, AUTH-06 operator decide denied (ledger untouched).
- Stubs for `identity.v1` / `risk.v1`; `scripts/run_rbac_fixture_probes.sh`.
- Honest labels: `sn009_authority_exercised=false`; RBAC path is not money-path evidence.
- Runbook + matrix docs for optional identity/risk peers.

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
- Default HTTP drivers hit payment-provider only (`path=provider-sandbox-only`).
- Authority HTTP path needs live peers + `SENTINEL_V1_AUTHORITY_PATH=1` (runbook).
- Passing fixture / sandbox checks are not product release or live-provider evidence.
