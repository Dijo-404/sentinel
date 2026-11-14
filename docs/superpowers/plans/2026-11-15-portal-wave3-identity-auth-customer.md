# Portal Wave 3: Identity / auth / customer (profile, notifications, workspaces, MFA/verify/forgot-reset)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace customer Profile/Notifications stubs and auth MFA/verify/forgot/reset/workspaces placeholders with DB-backed identity.v1 sandbox flows (real-peers fail closed).

**Architecture:** Extend `services/identity` Postgres + HTTP for profile update, notifications inbox, sandbox email-verify / MFA challenge / password reset (loopback delivery log — no real SMS/email). Web uses existing identity BFF (`/api/bff/identity`) and session cookies; pages never invent roster/notification rows.

**Tech Stack:** FastAPI identity, PostgreSQL, Next.js BFF (`apps/web`), Vitest/pytest.

**Spec:** `docs/superpowers/specs/2026-11-15-portal-db-backed-completion-design.md` (Wave 3 row)

## Global Constraints

- Contract baseline: `sentinel.task-contracts.v1` / SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`
- Product mode: `NEXT_PUBLIC_SHELL_MODE=real-peers`
- No UI mock product rows; seed Postgres; fail closed when peer/DB down
- Sandbox only: delivery codes go to identity delivery log / fixture store — never claim live SMS/email
- No money authority on these routes
- Worktree: `/home/dj/projects/sentinel-portal-wave0-1` on `feat/portal-wave3-identity-auth`; no push/`main` merge unless user asks
- Commit when each task says so

## Review Focus

- Unauthenticated password-reset / verify endpoints do not leak whether email exists (generic 202/OK)
- MFA challenge codes never returned in public JSON in real-peers (only delivery log / test hooks)
- Profile PATCH cannot escalate role/tenant/permissions
- Notifications scoped to session user
- Pages: no “Not available yet” / “Fixture placeholder” in real-peers product path

## Out of scope

- Customer Assistant (Wave 4)
- Admin remainder, evals/observability HTTP (Waves 4–5)
- Live IdP / Twilio / SendGrid

---

### Task 1: Identity profile read/update

**Files:**
- Modify: `services/identity/src/sentinel_identity/adapters/http.py`
- Modify: `services/identity/src/sentinel_identity/application/service.py`
- Modify: `services/identity/contracts/identity.v1.json` (additive routes)
- Create: `services/identity/tests/contract/test_profile.py`
- Modify: README/CHANGELOG

**Interfaces:**
- `GET /v1/auth/me` already returns user — ensure `display_name`, `email`, `preferred_language` present
- `PATCH /v1/auth/me` body `{ display_name?, preferred_language? }` → updated user public; reject unknown fields / role/tenant keys with 422
- Auth: Bearer session

- [ ] **Step 1: Failing contract tests** for PATCH success + privilege-field reject

- [ ] **Step 2: Implement + `make -C services/identity check` PASS**

- [ ] **Step 3: Commit** `feat(identity): PATCH /v1/auth/me profile`

---

### Task 2: Identity notifications store + list/mark-read

**Files:**
- Migration under `services/identity/migrations/` for `identity.notifications`
- Storage memory + postgres adapters
- HTTP: `GET /v1/auth/notifications`, `POST /v1/auth/notifications/{id}/read`
- Seed: ≥1 notification for `customer@example.test` (or matrix customer) when sandbox seed runs
- Tests + README/CHANGELOG

**Interfaces:**
- List → `{ "notifications": [ { "notification_id", "title", "body", "created_at", "read_at" | null } ] }` newest first, max 50
- Mark read → `{ "notification_id", "read_at" }`; 404 other-user
- Roles: any authenticated session for own notifications

- [ ] **Steps: TDD, check, commit** `feat(identity): notifications inbox`

---

### Task 3: Sandbox verify-email + MFA challenge + forgot/reset password

**Files:**
- Tables or reuse: `identity.auth_challenges` (type: email_verify | mfa | password_reset; code_hash; expires_at; consumed_at; user_id)
- Delivery log table/adapter (sandbox): append-only `{ channel: "loopback", destination, purpose, created_at }` — plaintext code **only** in test helper / `IDENTITY_EXPOSE_SANDBOX_CODES=true` for module checks, never default real-peers product
- Routes:
  - `POST /v1/auth/verify/request` `{ }` session → 202, creates email_verify challenge
  - `POST /v1/auth/verify/confirm` `{ code }` session → marks email verified on user
  - `POST /v1/auth/mfa/challenge` session → 202 (sandbox TOTP-or-code; document: numeric code via loopback)
  - `POST /v1/auth/mfa/verify` `{ code }` session → sets `mfa_verified_at` on session
  - `POST /v1/auth/password/forgot` `{ email }` → always 202
  - `POST /v1/auth/password/reset` `{ email, code, new_password }` → 200 or 400 invalid; on success updates hash + consumes challenge
- Wire into seed for one demo user with pending notification optional
- Contract tests covering no email enumeration on forgot

- [ ] **Steps: TDD, check, commit** `feat(identity): sandbox verify mfa password-reset`

---

### Task 4: Web identity client + BFF coverage for new routes

**Files:**
- Extend `IdentityClient` / real-peer client / fixture stub
- Confirm `/api/bff/identity/[...path]` passthrough (created Wave 2)
- Tests in `apps/web/tests`
- CHANGELOG

**Interfaces:**
- `getMe`, `patchProfile`, `listNotifications`, `markNotificationRead`, `requestVerify`, `confirmVerify`, `mfaChallenge`, `mfaVerify`, `forgotPassword`, `resetPassword`, `listWorkspaces`, `selectWorkspace` (reuse existing where present)

- [ ] **Steps: TDD, `make -C apps/web check`, commit** `feat(web): identity client auth surface extensions`

---

### Task 5: Auth pages — workspaces, verify, MFA, forgot, reset

**Files:**
- Replace placeholders:
  - `apps/web/src/app/auth/workspaces/page.tsx`
  - `apps/web/src/app/auth/verify/page.tsx`
  - `apps/web/src/app/auth/mfa/page.tsx`
  - `apps/web/src/app/auth/forgot-password/page.tsx`
  - `apps/web/src/app/auth/reset-password/page.tsx`
- Client panels under `apps/web/src/components/auth/`
- Browser tests: no “Fixture placeholder”; peer-error or success region
- Workspaces: list + select via BFF; set session cookie on select (reuse `switchActiveAssignment` / auth helpers)

- [ ] **Steps: TDD, check, commit** `feat(web): wire auth verify mfa reset workspaces`

---

### Task 6: Customer Profile + Notifications pages

**Files:**
- Replace: `apps/web/src/app/customer/(protected)/profile/page.tsx`
- Replace: `apps/web/src/app/customer/(protected)/notifications/page.tsx`
- Components: `profile-panel.tsx`, `notifications-panel.tsx`
- Browser tests: `customer-profile-notifications.test.tsx`
- `data-testid`: `customer-profile`, `customer-notifications`, `peer-error`
- Never “Not available yet”

- [ ] **Steps: TDD, check, commit** `feat(web): customer profile and notifications from identity`

---

### Task 7: Seed + verify-wave3

**Files:**
- Extend identity `make seed` / sandbox seed for profile fields, ≥1 notification, optional challenge fixtures for tests only
- `integration/core` verify-wave3: hit me/notifications (with session token), forgot returns 202, workspaces list
- Makefile target + README
- Update program index Wave 3 → done

- [ ] **Steps: TDD gate, check, commit** `feat(integration): wave 3 identity auth verify`

---

## Execution notes

- Prefer keeping notifications inside identity (builder default #3).
- Customer Assistant stays stub until Wave 4.
- After Task 7: stop for user push/PR unless asked to continue.
