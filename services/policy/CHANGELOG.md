# SN-005 changelog

## Unreleased

### Added — 13 November 2026

- Independent module ownership, architecture/interface guide, scoped agent rules and acceptance checklist.
- Installable `sentinel-policy` package with hatchling/uv, FastAPI `POST /v1/evaluate`, health/ready/capabilities routes.
- Framework-free `demo-policy-v1` rules: tenant/subject scope, payment eligibility, evidence freshness, fraud/chargeback, destination/amount, approval binding.
- Local principal token map, contract snapshots, digest fixture, unit and HTTP acceptance tests.
- Module `Makefile` targets: `setup`, `check`, `preview`.

### Implementation status

- Standalone `make -C services/policy check` is the component evidence path (fixture mode).
- Real-peer assembly with workflow/ledger remains unverified; no sibling imports.
- Contract pin: `sentinel.task-contracts.v1` SHA-256 `0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa`.
