# SN-016 changelog

## Unreleased

### Added — 13 November 2026

- Independent module ownership, architecture/interface guide, scoped agent rules and acceptance checklist.
- `sentinel-evaluation` package implementing `evaluation.v1`: versioned fixture dataset, injected local/HTTP candidate runners, deterministic safety/outcome scoring, holdout-aware detail reports.
- Local conforming candidate and deliberately unsafe doubles (unauthorized, over-refund, cross-tenant, duplicate-effect, false-credit).
- `core-assembly.v1` stubs under `tests/stubs/core_assembly/` plus real-peer fail-closed probe (no silent fixture fallback).
- Module `make check` (`uv sync`, ruff, pytest, `sentinel-evaluation self-test`), `.env.example`, contract snapshots.

### Implementation status

- Standalone fixture self-tests cover acceptance and negative assembly cases.
- Real assembled core-assembly / product safety certification remain owner-run and unverified.
- Fixture pass is not release evidence.
