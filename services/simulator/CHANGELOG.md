# SN-004 changelog

## Unreleased

### Changed — 14 November 2026

- Default tenant `tenant-demo`; canonical tokens `tok-workflow` / `tok-verifier` / `tok-dispatcher` / `tok-sandbox-admin` (legacy `*-demo` aliases kept). Refs #77.

### Added — 13 November 2026

- Independent module ownership, architecture/interface guide, scoped agent rules and acceptance checklist.
- Standalone `sentinel-simulator` package: FastAPI `payment-provider.v1` routes, seeded DEMO-ORDER-42 dual-capture fixture, bearer principal map, and in-memory store.
- Deterministic fault controls (outage, delay, timeout-after-accept, duplicate events, out-of-order credit) with inspectable refund stats.
- Separate provider-confirm and credit-confirm admin paths so provider outcome and credit stay distinct events.
- Module `make check` (uv sync, ruff, pytest), `.env.example`, contract snapshot, and demo fixture.

### Implementation status

- Module-local fixture checks cover acceptance criteria and fault/auth boundaries.
- Assembled real-peer product wiring and external pilot settlement remain owner-run / unverified.
