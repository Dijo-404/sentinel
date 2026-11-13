# SN-005 changelog

## Unreleased

### Changed — 14 November 2026

- Principals default tenant `tenant-demo`; accepts `tok-workflow` (keeps `workflow-demo-token` alias). Refs #77.

### Fixed

- Empty `case_ids` deny; `*` allows all cases (deny-by-default). Demo `star-scope-demo-token` fixture added.

### Added — 13 November 2026

- Independent module ownership, architecture/interface guide, scoped agent rules and acceptance checklist.
- Installable `sentinel-policy` package with hatchling/uv, FastAPI `POST /v1/evaluate`, health/ready/capabilities routes.
- Framework-free `demo-policy-v1` rules: tenant/subject scope, payment eligibility, evidence freshness, fraud/chargeback, destination/amount, approval binding.
- Local principal token map, contract snapshots, digest fixture, unit and HTTP acceptance tests.
- Module `Makefile` targets: `setup`, `check`, `preview`.

### Implementation status

- Standalone `make -C services/policy check` is the component evidence path (fixture mode).
- Real-peer assembly with workflow/ledger remains unverified; no sibling imports.
- Contract pin: `sentinel.task-contracts.v1` SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.
