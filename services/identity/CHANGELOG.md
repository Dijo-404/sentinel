# SN-035 changelog

## Unreleased

### Added — sandbox verify / MFA / password reset

- `POST /v1/auth/verify/request|confirm`, `/v1/auth/mfa/challenge|verify`,
  `/v1/auth/password/forgot|reset`.
- `identity.auth_challenges` + append-only `identity.auth_delivery_log`
  (loopback channel); `users.email_verified_at`.
- MFA / verify / reset codes are hashed at rest. Plaintext appears only via
  store peek helper or `IDENTITY_EXPOSE_SANDBOX_CODES=true` (fixture/module
  checks). Flag is refused in `real-peers` mode. Public JSON never includes
  codes by default. Forgot always returns 202 (no email enumeration).

### Added — notifications inbox

- `GET /v1/auth/notifications` returns the caller's inbox (newest first, max 50).
- `POST /v1/auth/notifications/{id}/read` marks own notification read; other-user
  or missing id → 404.
- Migration `0004_notifications.sql` adds `identity.notifications`.
- Sandbox seed includes ≥1 unread notification for `customer@example.test`.

### Added — self-service profile PATCH

- `PATCH /v1/auth/me` updates `display_name` / `preferred_language` for the
  bearer session. Unknown and privilege fields (`role`, `tenant_id`, …) return
  422. `GET /v1/auth/me` user public always includes those profile fields.
- Migration `0003_preferred_language.sql` adds `identity.users.preferred_language`.

### Added — supervisor-safe ops team roster

- `GET /v1/ops/team`: active operator/supervisor assignments for the caller's
  tenant. Allowed for `supervisor` and `platform_admin` sessions.
  Does not replace `/v1/admin/users` (still platform_admin-only).

### Fixed — admin invite duplicate active email (#129)

- `admin_invite` rejects when `work_email` already belongs to an active user
  (`ConflictError` / HTTP 409, same message as customer register:
  `Account already exists`). No PENDING invitation is created for seeded
  emails such as `operator@example.test`.

### Fixed — staff invitation delivery (finding #11)

- Durable `invitation_delivery_outbox` (Postgres migration `0002` + memory stub):
  plaintext invite tokens no longer live only in process memory.
- Sandbox delivery consumer drains pending outbox into a local inbox with
  acceptance links (`GET /v1/sandbox/inbox`, `POST /v1/sandbox/delivery/drain`).
  No production email provider; evidence labeled `sandbox_inbox`.
- Invite path auto-drains after enqueue so local demo can read the link after
  restarts that preserve store state.

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
