# SN-035 changelog

## Unreleased

### Added — merchant self-signup + email login signals (#154)

- `POST /v1/auth/merchant/register`: merchant user + assignment in `tenant-demo`
  with server-generated `merchant_ref`; privileged fields (now also
  `merchant_ref`, `subject`) rejected; duplicate email 409 like customer.
- `POST /v1/auth/login`: input validation first (422), then distinct
  `ACCOUNT_NOT_FOUND` (404) for unknown email; wrong password stays generic 401.
- Bounded in-memory login failure limiter: 5/(email, client IP) and 20/known client IP per 15 min
  → 429 `RATE_LIMITED`. `IDENTITY_TRUSTED_PROXIES` gates `X-Forwarded-For`.
- Multi-workspace login without `requested_role` now returns 200 with
  `active_assignment: null` and an unscoped session (no permissions) instead of
  409, so clients can use `GET /v1/auth/workspaces` + `POST .../select`.

### Fixed — login limiter trust, denial-of-service and capacity (#154)

- Explicit proxy allowlist (empty default), validated forwarded IPs, and original
  socket preservation in the CLI. Missing proxy client IP never shares a BFF bucket.
- Another client's email failures cannot block correct credentials; unknown-client
  email fallback limits failed responses only. Successful login clears its own pair.
- Atomic failure admission under a lock; prune expired keys, reject capacity
  overflow without evicting active limits. Counters remain single-process only.
- Signup/login now consistently reject malformed email; JSON auth fields must be
  strings instead of implicitly converting null, numbers or objects to credentials.
- Regressions cover proxy absence/spoofing/malformed IP, account-targeted attacks,
  capacity recovery/retention and concurrent failure admission.

### Added — labeled sandbox/dev-deploy credentials

- Document portal seed accounts under `deploy/dev/CREDENTIALS.md` with shared
  password `demo-password` (`IDENTITY_DEMO_PASSWORD`).
- `SENTINEL_SANDBOX_PUBLIC_BIND=1` opt-in allows non-loopback bind while demo
  seed passwords remain configured (sandbox/dev-deploy only).
- Treat `demo-password` as a demo credential in bind safety.

### Fixed — admin tenants / teams invent no fallback rows

- `admin_list_tenants` / `admin_list_teams` return only store-derived rows.
  Empty catalogs stay empty; seed still supplies `tenant-demo` /
  `payments-support` via fixtures, not API invention.

### Added — admin tenants / teams / security projections

- `GET /v1/admin/tenants` → `{ tenants: [{ tenant_id, display_name, status }] }`
  from active assignments + user home tenants.
- `GET /v1/admin/teams` → `{ teams: [{ team_id, name, member_count }] }` from
  assignment `team_id` aggregates (seed `payments-support`).
- `GET /v1/admin/security` → counts only:
  `mfa_verified_sessions`, `active_sessions`, `suspended_users`, `updated_at`.
- Contract tests cover roles, audit-events, and the three new projections.

### Fixed — sandbox latest-code inbox for auth challenges

- When `IDENTITY_SANDBOX` or `SENTINEL_V1_SANDBOX` is truthy, persist challenge
  plaintext in `auth_delivery_log.sandbox_code` (migration `0007`). Never when
  sandbox flag false.
- `GET /v1/auth/sandbox/latest-code?purpose=email_verify|mfa` (Bearer) → `{ code }`
  or 404 when flag off / no open challenge.
- `GET /v1/auth/sandbox/password-reset-code?email=` requires
  `X-Identity-Sandbox-Token` = `IDENTITY_SANDBOX_TOKEN` (constant-time); identical
  404 for bad token / unknown email / missing challenge.
- Forgot 202 includes identical `sandbox_hint` when sandbox on (no email enum).
- Real-peers + sandbox allowed (product demo). `IDENTITY_EXPOSE_SANDBOX_CODES`
  still refused in real-peers.

### Added — 15 November 2026 (portal wave 3 make seed)

- `sentinel-identity seed` / `make seed`: load `fixtures/seed_users.json` into
  Postgres (`IDENTITY_DATABASE_URL`) — profile fields + ≥1 notification for
  `customer@example.test`. Challenge OTP fixtures stay test-only
  (`IDENTITY_EXPOSE_SANDBOX_CODES` / memory peek); never written by seed.

### Fixed — harden sandbox auth challenges

- Challenge codes are 8+ char alphanumeric (not 6-digit). Failed verifies
  increment `attempt_count`; challenge locks/consumes after **N=5** failures.
- Atomic consume: conditional `UPDATE … WHERE consumed_at IS NULL AND expires_at > at`.
- Durable Postgres `auth_delivery_log` dropped legacy `raw_code`; sandbox
  plaintext returns via gated `sandbox_code` + inbox GETs (see above).
- `build_app` refuses `expose_sandbox_codes` when `mode=real-peers` even if
  Settings is constructed manually.

### Added — sandbox verify / MFA / password reset

- `POST /v1/auth/verify/request|confirm`, `/v1/auth/mfa/challenge|verify`,
  `/v1/auth/password/forgot|reset`.
- `identity.auth_challenges` + append-only `identity.auth_delivery_log`
  (loopback channel); `users.email_verified_at`.
- MFA / verify / reset codes are hashed at rest. Plaintext appears only via
  in-memory peek helper or `IDENTITY_EXPOSE_SANDBOX_CODES=true` (fixture/module
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
  bearer session. Unknown and privilege fields (`role`, `tenant_id`, …) return 422. `GET /v1/auth/me` user public always includes those profile fields.
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
