# SN-022 changelog

## Unreleased

### Added — 13 November 2026

- Independent module ownership, architecture/interface guide, scoped agent rules and acceptance checklist.
- `finharness-runtime.v1` package: pinned-case runtime, shadow comparison, sandbox routing, restart-safe unknown-action reconcile.
- Durable `JsonCaseStore` pins/unknown-actions; `ShadowSafetyGuard` + `ReadOnlyLedger` block second refund / notifications / credentials on shadow path.
- Local stubs under `tests/stubs/` for finharness-sdk, indic-context, evidence, policy, action-ledger, verifier (valid/unavailable/malformed/unauthorized).
- Real-peer adapters fail closed when URLs absent; `contracts/COMPATIBILITY.md` checklist.
- Module `Makefile` `setup`/`check`/`preview`, lockfile, `.env.example`, fixtures, contract snapshot.

### Implementation status

- Standalone fixture checks only. Real-peer assembly, payment simulator, live model, and product release evidence remain unverified.
- No independent refund executor or ledger tables; SN-009 remains sole financial authority.
