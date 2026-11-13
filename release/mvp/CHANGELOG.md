# SN-019 changelog

## Unreleased

### Added — 13 November 2026

- Independent module ownership, architecture/interface guide, scoped agent rules and acceptance checklist.
- `release-evidence.v1` verification kit: manifest validation, artifact integrity,
  clean-checkout/demo procedure CLI, release-report rendering.
- Positive/negative local manifests under `contracts/manifests/`; artifact digest
  fixtures under `contracts/artifacts/`.
- Peer stubs for `core-assembly.v1`, `evaluation.v1`, `replay.v1`, `telemetry.v1`
  (valid / unavailable / malformed / unauthorized_or_out_of_scope).
- Real-peer adapter with explicit failure (no fixture fallback).
- Module-local `make setup` / `make check` / `make preview`; stdlib-only package.

### Implementation status

- Kit self-tests pass with no product peers. Fixture-only evidence never yields
  `release_approved` under `--strict-release`.
- Assembled product / owner-run MVP release acceptance remains unverified and
  out of scope for this component task.
