# SN-016 changelog

## Unreleased

### Changed (finding #13)

- Replaced reject-only real-assembly placeholder with `HttpAssemblyPeer`
  that probes `/healthz` + `/v1/capabilities` when a URL is configured.
- Local reference peers remain `StubAssemblyPeer` (`assembly_stub=valid|…`).
- `assembly_stub=live` uses HTTP; missing/unreachable peers fail closed.

### Added — 13 November 2026

- Independent module ownership, architecture/interface guide, scoped agent rules and acceptance checklist.
- `sentinel-evaluation` package implementing `evaluation.v1`: versioned fixture dataset, injected local/HTTP candidate runners, deterministic safety/outcome scoring, holdout-aware detail reports.
- Local conforming candidate and deliberately unsafe doubles (unauthorized, over-refund, cross-tenant, duplicate-effect, false-credit).
- `core-assembly.v1` stubs under `tests/stubs/core_assembly/` plus real-peer fail-closed probe (no silent fixture fallback).
- Module `make check` (`uv sync`, ruff, pytest, `sentinel-evaluation self-test`), `.env.example`, contract snapshots.

### Implementation status

- Standalone fixture self-tests cover acceptance and negative assembly cases.
- Local reference assembly stubs + HTTP capabilities probe path exercised in-module.
- Live product safety certification against a full assembled stack remains owner-run.
- Fixture pass is not release evidence.
