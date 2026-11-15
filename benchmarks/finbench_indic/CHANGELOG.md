# SN-023 changelog

## Unreleased

### Added — Paytm-shaped FinBench groups

- `paytm_dup_010` (en/ta/hi/code-mix/wrong-amount/injection/ambiguous), `paytm_mismatch_011`,
  `paytm_unauthorized_012`. Same-group variants stay in one split. Synthetic provenance;
  amounts mirror ₹10 staging-shaped simulator pack.

### Fixed — live candidate honesty

- `LiveModelCandidate` requires an injected context peer when enabled; refuses
  gold-copy of expected fields labeled `live`. CLI `--live-model` needs
  `--context-peer`; optional `--runtime-peer` disclosed under report peers.

### Added — 13 November 2026

- Independent module ownership, architecture/interface guide, scoped agent rules and acceptance checklist.
- `finbench.v1` package: hashed grouped synthetic dataset `indic-fin-v0.1.0`, deterministic scoring with separate model/system channels, hard-safety gate independent of averages.
- Injected candidates: recorded baseline, fake model, opt-in live (no silent fake fallback), deterministic system, unsafe regression fault demo.
- Real-peer adapters for `finharness-runtime.v1` and `indic-context.v1` that fail closed on unavailable/malformed/unauthorized peers.
- Local stubs under `tests/stubs/` covering valid, unavailable, malformed, unauthorized_or_out_of_scope for both consumed ports.
- CLI (`sentinel-finbench` / `finbench`): `run`, `self-test`, `probe-peers`.
- Module Makefile `setup`/`check`/`preview`, lockfile, `.env.example`, contract snapshot and compatibility checklist.

### Implementation status

- Standalone fixture/recorded checks only. Real assembled runtime/context peers, payment simulator runs, live provider calls, and product release evidence remain unverified.
- Dataset is synthetic and small; language quality is not native-speaker certified.
