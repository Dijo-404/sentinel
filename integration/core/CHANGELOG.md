# SN-014 changelog

## Unreleased

### Added — 13 November 2026

- Independent module ownership, architecture/interface guide, scoped agent rules and acceptance checklist.
- `sentinel-core-assembly` package producing `core-assembly.v1` with fixture and strict `real-peers` modes.
- Four journey drivers against local reference peers: pending, merchant mismatch, duplicate payment (150000-paise approval/timeout/credit recovery), refund-pending.
- Peer stub matrix under `tests/stubs/` for all seven consumed ports (`valid`, `unavailable`, `malformed`, `unauthorized_or_out_of_scope`).
- Makefile `check` target, contract snapshot, duplicate-payment fixture, and CLI self-test.
- Strict assembly rejects missing/incompatible peers and fixture evidence labeled as real; harness PASS never sets `assembled_mvp_claimed`.

### Implementation status

- Module-local fixture harness and negative strict-mode diagnostics are implemented and covered by `make -C integration/core check`.
- Real HTTP peer journey wiring remains owner-selected; probe adapter is present, end-to-end real-component assembly is unverified until exercised outside this module.
- Passing fixture checks are not product release evidence.
