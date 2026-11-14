# SN-035 changelog

## Unreleased

### Fixed — ponytail identity gaps

- `GET /v1/merchant-memberships?tenant_id=&merchant_ref=` projects active
  merchant-scoped role assignments as `{contract_version, memberships[]}` for
  merchant-teams real-peer sync (`platform_admin` or matching merchant staff).
- Password floor: register + new-invite accept require length ≥ 8.
- Login with multiple active assignments and no `requested_role` returns 409
  without minting a session.

### Added — SN-040 peer principal catalog

- Explicit money-path denylist for `merchant` / `risk_officer` / `platform_admin`;
  supervisor alone holds `financial.approval.decide`. Refs #103.
- `contracts/COMPATIBILITY.md` checklist; principals catalog metadata
  (`catalog_extension`, `money_authority_roles`, `money_forbidden_roles`).
- Unit coverage: extended roles cannot be treated as supervisor for decide.

### Fixed

- Atomic invitation consume before assignment (AUTH-03 double-grant).
- Privileged invite/grant requires independent `privileged-changes` decision
  before usable activation (AUTH-12); deny privileged self-grant.
- Admin invite API returns `delivery_hint` only (no plaintext invite token).
- Admin users list is staff-only; grant/revoke bundles authz_version + session
  revoke atomically where the store supports it.
- Omit plaintext passwords from committed fixtures; hash at seed from
  `IDENTITY_DEMO_PASSWORD` (default `x`). Branch history rewritten to drop
  prior Generic Password finding.

### Added

- Independent `identity.v1` HTTP service: customer register/login, sessions,
  workspace select, staff invitation accept, Platform Admin invite/grant/revoke/
  suspend/reactivate, audit list, and capabilities probe.
- Domain invariants: customer-only self-register; deny customer/service roles on
  staff invite/grant; `authz_version` bump on grant/revoke/suspend; session
  token hashing; revoke-all on suspend.
- In-memory fixture store, PostgreSQL adapter + migration DDL, seeded six human
  roles plus negative cross-tenant principal, contract snapshot, bind-safety
  refuse of demo tokens on non-loopback.
- Module-local `make check` (ruff + pytest) covering AUTH-01…05(partial), 11,
  13, 15.
- Contract pin: `sentinel.task-contracts.v1` SHA-256
  `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.
