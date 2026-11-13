# SN-026 changelog

## Unreleased

### Added — 13 November 2026

- Independent module ownership, architecture/interface guide, scoped agent rules and acceptance checklist.
- `sentinel-sandbox-pilot` package producing `sandbox-validation.v1` with fixture and strict `real-peers` modes.
- Validation drivers against local reference peers: second-workflow, load, restart, restore, kill-switch, rollback.
- Restart/restore/rollback preserve stable `action_id` / `provider_ref`; kill switch blocks new writes while reconciliation continues.
- Peer stub matrix under `tests/stubs/` for all five consumed ports (`valid`, `unavailable`, `malformed`, `unauthorized_or_out_of_scope`).
- Makefile `check` target, contract snapshot, in-flight action fixture, and CLI self-test.
- Strict mode rejects missing/incompatible peers and fixture evidence labeled as real; absent external authorization cannot yield a successful pilot verdict; kit PASS never sets `external_pilot_claimed`.

### Implementation status

- Module-local fixture harness and negative strict-mode diagnostics are implemented and covered by `make -C validation/sandbox-pilot check`.
- Real HTTP peer driver wiring remains owner-selected; probe adapter is present, end-to-end real-component / external pilot evidence is unverified until separately authorized and exercised.
- Passing fixture checks are not external pilot or product release evidence.
