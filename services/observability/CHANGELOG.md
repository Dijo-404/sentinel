# observability changelog

## Unreleased

### Added

- `observability.v1` HTTP+Postgres peer on port `8033`: `POST /v1/ingest`,
  `GET /v1/signals`, `GET /v1/spans` (newest first, max 50),
  health/ready/capabilities with `financial_audit: false`.
- Span wire fields align with `packages/telemetry` `RecordedSpan`
  (`name`, `attributes`, `events`); never claims financial audit.
- `make seed` / `sentinel-observability seed` writes one synthetic span for
  `tenant-demo` when `OBSERVABILITY_DATABASE_URL` is set
  (idempotent upsert; evidence label synthetic-sandbox).
