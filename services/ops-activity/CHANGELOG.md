# ops-activity changelog

## Unreleased

### Added

- `ops-activity.v1` HTTP+Postgres peer on port `8029`: `GET /v1/activity`
  (newest first, max 50), health/ready/capabilities.
- `make seed` / `sentinel-ops-activity seed` writes synthetic activity for
  `tenant-demo` / `case-demo-42` when `OPS_ACTIVITY_DATABASE_URL` is set
  (idempotent upsert; evidence label synthetic-sandbox).
- Documented case-api projection as sync stub (local rows only).
