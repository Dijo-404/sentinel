# SN-035 — Identity and access service

Standalone `identity.v1` service: users, sessions, invitations, role grants,
authz versioning, and identity audit. No money authority.

**Owned root:** `services/identity/` · **Branch:** `feat/sn-035-identity`

Contract: `sentinel.task-contracts.v1`, SHA-256
`0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.

## Scope

- Customer self-register (customer role only; privileged fields ignored/rejected;
  password length ≥ 8)
- Merchant self-register `POST /v1/auth/merchant/register` (owner ruling, #154):
  `display_name`, `email`, `password`, `business_name`, optional
  `preferred_language`. Creates a `staff` user plus one active `merchant`
  assignment in `tenant-demo` with a server-generated `merchant_ref`
  (`merchant-<12 hex>`, scope `tenant:tenant-demo|merchant:<ref>`). Same
  validation, password floor, email-verify flow and 409 `CONFLICT` duplicate
  handling as customer register. Privileged keys (`role`, `roles`, `role_id`,
  `tenant_id`, `subject`, `subject_refs`, `merchant_ref`, `account_type`,
  `permissions`, …) → 422. Identity has no merchant-org table: `business_name`
  is returned and kept in the `merchant.registered` audit event; a merchant-teams
  org record (if needed) is a separate peer step. Operator, supervisor, risk
  officer and platform admin stay invite-only.
- Login / logout / me / `PATCH /v1/auth/me` profile (`display_name`,
  `preferred_language`; privilege fields rejected) / notifications inbox
  (`GET /v1/auth/notifications`, `POST .../{id}/read`) / sandbox verify-email,
  MFA challenge (numeric loopback code), forgot/reset password /
  workspaces select with hashed session tokens (multi-role login without
  `requested_role` returns `active_assignment: null` and an unscoped session with
  no permissions until `POST /v1/auth/workspaces/select`)
- Platform Admin invite / grant / revoke / suspend / reactivate / list / audit
- Accept invitation (single-use; deny expired/revoked/mismatched; new password ≥ 8)
- Sandbox invite delivery: durable outbox + `GET /v1/sandbox/inbox` acceptance links
  (local demo only; set `IDENTITY_ACCEPT_LINK_BASE`, default `http://127.0.0.1:3000`)
- Sandbox auth challenges: 8+ char alphanumeric codes hashed at rest; fail-closed
  after **N=5** bad attempts per challenge; atomic consume. Plaintext OTP persists
  only when `IDENTITY_SANDBOX=true` or `SENTINEL_V1_SANDBOX=true` (column
  `auth_delivery_log.sandbox_code`). Session inbox:
  `GET /v1/auth/sandbox/latest-code?purpose=email_verify|mfa` → `{ code }` (404 when
  sandbox flag off). Password-reset inbox (no session):
  `GET /v1/auth/sandbox/password-reset-code?email=` requires
  `X-Identity-Sandbox-Token` = `IDENTITY_SANDBOX_TOKEN` (constant-time); identical
  404 for bad token / unknown email / missing challenge. Forgot always 202; when
  sandbox on, includes identical `sandbox_hint` (no email enumeration).
  `IDENTITY_EXPOSE_SANDBOX_CODES=true` still injects `sandbox_code` into 202 bodies
  for fixture/module checks only (refused in real-peers).
- `GET /v1/merchant-memberships` for merchant-teams identity peer projection
- `GET /v1/ops/team` supervisor-safe tenant roster (operator + supervisor only;
  not full `/v1/admin/users`)
- `authz_version` bump + session denial after revoke/suspend
- Seeded synthetic accounts for six human roles + cross-tenant negative

**Ruling (portal Wave 2 Team):** Supervisors must not require platform_admin.
Use `GET /v1/ops/team` for the supervisor Team page. Keep `GET /v1/admin/users`
for Platform Admin staff directory only.

**Non-goals:** ledger approvals, provider writes, Case API ownership, portal UI
(M2 admin UI / M1.3 web auth live in `apps/web`). Service principals never get
interactive logins.

## Login signals and account enumeration (#154)

`POST /v1/auth/login` outcomes:

| Condition                                                                           | HTTP | `code`                   |
| ----------------------------------------------------------------------------------- | ---- | ------------------------ |
| Missing email/password or email without `@`                                         | 422  | `INVALID_INPUT`          |
| ≥ 5 failures for this (email, client IP), ≥ 20 for known client IP, or limiter full | 429  | `RATE_LIMITED`           |
| No account for this email                                                           | 404  | `ACCOUNT_NOT_FOUND`      |
| Wrong password for an existing account                                              | 401  | `UNAUTHORIZED` (generic) |
| Account not active / no workspace                                                   | 403  | `FORBIDDEN`              |

**Trade-off (owner decision):** `ACCOUNT_NOT_FOUND` lets the web send unknown
emails to sign-up, and it also tells anyone whether an email is registered.
Mitigations: wrong passwords stay generic; unknown-email and wrong-password
attempts both count toward **5 failures per (email, client IP)** and **20 per
known client IP** in 15 minutes; a successful login clears only its own account/client
bucket, never the IP bucket or another client's limits. An attacker on another IP
cannot block a correct login solely by targeting that email. Missing/invalid client
IP uses a per-email fallback for failed responses; correct credentials are verified
and accepted regardless of that fallback count. This fallback does not bound password
hashing work; configure verified client propagation and ingress abuse controls before
exposing the service. Returns 429 when limited.

Limits are thread-safe, bounded process memory (`LoginRateLimiter`, ≤ 10 000 keys).
Expired keys are pruned before admission; a full store rejects new keys without
evicting active limits. They are not shared across replicas. **Use one identity
process only** until counters are moved to a shared store.

Deployment client-IP trust is explicit: `IDENTITY_TRUSTED_PROXIES` is a comma-separated
list of exact direct BFF/proxy socket addresses, **empty by default**, including
loopback only when explicitly configured. Only those peers may supply
`X-Forwarded-For`; the rightmost address must parse as an IP literal. Trusted BFFs
without a valid forwarded address have unknown client IP, never a shared BFF IP
bucket. Direct untrusted clients use the socket IP and their forwarded headers are
ignored. The CLI disables Uvicorn proxy-header rewriting so this check sees the
original socket peer. Alternate ASGI launch commands must likewise disable proxy
headers (`--no-proxy-headers`).

The web BFF must verify its ingress before forwarding a single actual client IP.
The matching web change uses server-only `WEB_TRUSTED_INGRESS_TOKEN` (≥32 characters),
`x-sentinel-ingress-token` and a single literal `x-sentinel-client-ip`. Configure
the ingress to strip/overwrite incoming copies, inject the private token and derive
the address from its transport; never expose/log that token or use `NEXT_PUBLIC_*`.
Restrict identity access to that BFF plus explicitly intended direct peers. This
module does not modify deployment ingress configuration. Without this configuration,
a BFF cannot provide per-client IP abuse protection; the fallback behavior above
keeps unrelated accounts usable.

## Standalone setup

```sh
cd services/identity
cp .env.example .env   # optional; fixture mode needs no peers
make check
```

`make check` runs `uv sync --frozen`, ruff, and pytest against the in-memory
store. No sibling Sentinel services, Docker, or payment credentials required.

## Run (fixture mode)

```sh
export IDENTITY_MODE=fixture
make preview
# listens on 127.0.0.1:8012
```

Default bind: `127.0.0.1:8012` (documented free port). Non-loopback bind refuses
demo seed credentials (`bind_safety`). Fixture mode loads seed principals on
serve when `IDENTITY_SEED` is truthy (default).

## Postgres seed (real-peers / portal wave 3)

```sh
export IDENTITY_DATABASE_URL=postgresql+psycopg://identity:identity@127.0.0.1:5432/identity
make seed
# prints JSON {"status":"PASS","rows":…,"notification_id":"…",…}
```

Loads `fixtures/seed_users.json` (profile fields + ≥1 notification). Challenge
OTP codes stay test-only — never written by `make seed`. Assembly harness:
`IDENTITY_DATABASE_URL` set → `make -C integration/core seed-sandbox` invokes
this hook. Live verify: `make -C integration/core verify-wave3`.

## Sandbox demo flow (auth challenges)

Product-demo path works in **real-peers + Postgres** when sandbox flags are on
(distinct from `IDENTITY_EXPOSE_SANDBOX_CODES`, which stays refused in real-peers).

```sh
export IDENTITY_MODE=real-peers
export IDENTITY_DATABASE_URL=postgresql+psycopg://identity:identity@127.0.0.1:5432/identity
export IDENTITY_SANDBOX=1          # or SENTINEL_V1_SANDBOX=1
export IDENTITY_SANDBOX_TOKEN=local-demo-token
make preview
```

1. Login → Bearer session.
2. `POST /v1/auth/verify/request` or `/v1/auth/mfa/challenge` (202, no code in body).
3. `GET /v1/auth/sandbox/latest-code?purpose=email_verify|mfa` with Bearer → `{ "code": "…" }`.
4. Confirm / verify with that code.
5. Forgot: `POST /v1/auth/password/forgot` → 202 + `sandbox_hint` (same for unknown email).
6. Reset inbox: `GET /v1/auth/sandbox/password-reset-code?email=…` with header
   `X-Identity-Sandbox-Token: $IDENTITY_SANDBOX_TOKEN` → `{ "code": "…" }` or identical 404.
7. Sandbox flag off → both GET inboxes return 404; delivery log `sandbox_code` stays NULL.

## Seeded fixture principals

See `fixtures/seed_users.json` and `contracts/principals.json`. Seed JSON has
no plaintext passwords; hashes are derived at load time from
`IDENTITY_DEMO_PASSWORD` (portal/dev-deploy: `demo-password`; unset default `x`).
See [deploy/dev/CREDENTIALS.md](../../deploy/dev/CREDENTIALS.md).

| Email                       | Role           | Tenant       |
| --------------------------- | -------------- | ------------ |
| customer@example.test       | customer       | tenant-demo  |
| merchant@example.test       | merchant       | tenant-demo  |
| operator@example.test       | operator       | tenant-demo  |
| supervisor@example.test     | supervisor     | tenant-demo  |
| risk@example.test           | risk_officer   | tenant-demo  |
| admin@example.test          | platform_admin | tenant-demo  |
| admin-reviewer@example.test | platform_admin | tenant-demo  |
| outsider@other.test         | operator       | tenant-other |

## Evidence labels

| Dimension            | This module check                         |
| -------------------- | ----------------------------------------- |
| Component under test | Real `identity` implementation            |
| Storage              | In-memory fixture (`make check`)          |
| Postgres adapter     | Present; optional `@pytest.mark.postgres` |
| Payment / ledger     | N/A (no money authority)                  |
| Portal UI / BFF      | UNVERIFIED (M2 / SN-038)                  |
