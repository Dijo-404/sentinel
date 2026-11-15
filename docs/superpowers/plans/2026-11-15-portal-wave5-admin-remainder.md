# Portal Wave 5: Admin remainder pages

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace all admin “Not available yet” stubs (roles, tenants, teams, policies, security, integrations, merchants, AI, evaluations, observability, audit) with BFF → peer → DB (or honest empty/peer-error).

**Architecture:** Prefer existing Wave 3–4 APIs. Extend identity for tenants/teams/security/audit already partially present; add policy artifact list; add admin merchants list on merchant-teams; wire platform-ai / evals / observability / integrations. Shared thin `AdminPeerPanel` OK. No money authority on admin intel pages.

**Tech Stack:** identity, policy, merchant-teams, platform-ai, evals/core, observability, Next.js BFF.

**Spec:** `docs/superpowers/specs/2026-11-15-portal-db-backed-completion-design.md` (Wave 5)

## Global Constraints

- Contract baseline SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`
- `NEXT_PUBLIC_SHELL_MODE=real-peers`; no invented UI rows
- Admin pages require `admin` / `platform_admin` session via existing `requireRole("admin")`
- Worktree: `/home/dj/projects/sentinel-portal-wave0-1` · `feat/portal-wave5-admin-remainder`
- Commit per task; no push unless asked

## Review Focus

- Every listed stub loses “Not available yet”
- Peer down → `data-testid="peer-error"`
- Admin GETs do not expose password hashes or sandbox OTPs
- Policies page lists versioned artifacts — does not edit ledger rules

## Page → peer map (binding)

| Page          | Peer / route                                                                               |
| ------------- | ------------------------------------------------------------------------------------------ |
| Roles         | identity `GET /v1/admin/roles`                                                             |
| Audit         | identity `GET /v1/admin/audit-events`                                                      |
| Tenants       | identity `GET /v1/admin/tenants` (add if missing)                                          |
| Teams         | identity `GET /v1/admin/teams` (add if missing; assignment aggregates OK)                  |
| Security      | identity `GET /v1/admin/security` (add: MFA/session summary counts from DB)                |
| Policies      | policy `GET /v1/policies` (add list of versioned policy ids)                               |
| Merchants     | merchant-teams `GET /v1/admin/merchants` (add)                                             |
| Integrations  | platform-ai `GET /v1/integrations` (add thin seeded rows) OR identity — prefer platform-ai |
| AI            | platform-ai `GET /v1/config` + `GET /v1/runs`                                              |
| Evaluations   | evals `GET /v1/reports`                                                                    |
| Observability | observability `GET /v1/signals` (or spans)                                                 |

---

### Task 1: Identity admin tenants / teams / security projections

**Files:** `services/identity/` HTTP + service + tests + seed + contract JSON + CHANGELOG

**Interfaces:**

- `GET /v1/admin/tenants` → `{ tenants: [{ tenant_id, display_name?, status }] }` — at least `tenant-demo` from seed/assignments
- `GET /v1/admin/teams` → `{ teams: [{ team_id, name, member_count }] }` derived from assignments/team_id or synthetic sandbox team row
- `GET /v1/admin/security` → `{ mfa_verified_sessions, active_sessions, suspended_users, updated_at }` counts only
- Existing `GET /v1/admin/roles` and `GET /v1/admin/audit-events` remain; add tests if thin

- [ ] **Steps: TDD, `make -C services/identity check`, commit** `feat(identity): admin tenants teams security`

---

### Task 2: Policy artifact list + seed

**Files:** `services/policy/`

**Interfaces:**

- `GET /v1/policies` → `{ policies: [{ policy_id, version, status, updated_at }] }` including `demo-policy-v1`
- Auth: platform_admin / workflow / sandbox token as peer pattern allows; document
- No mutate-from-UI of evaluate rules in this wave

- [ ] **Steps: TDD, check, commit** `feat(policy): list versioned policy artifacts`

---

### Task 3: Merchant-teams admin merchants list

**Files:** `services/merchant-teams/`

**Interfaces:**

- `GET /v1/admin/merchants` → `{ merchants: [{ merchant_ref, display_name?, status }] }` from DB/seed (`merchant-demo-1`)
- platform_admin / sandbox-admin bearer

- [ ] **Steps: TDD, check, commit** `feat(merchant-teams): admin merchants list`

---

### Task 4: Platform-ai integrations list

**Files:** `services/platform-ai/`

**Interfaces:**

- `GET /v1/integrations` → `{ integrations: [{ integration_id, name, status, updated_at }] }` seeded ≥1 synthetic
- Keep money_authority false

- [ ] **Steps: TDD, check, commit** `feat(platform-ai): integrations list`

---

### Task 5: Web BFFs for evals / observability / platform-ai / policy

**Files:**

- `apps/web/src/app/api/bff/evals/[...path]/route.ts`
- `apps/web/src/app/api/bff/observability/[...path]/route.ts`
- `apps/web/src/app/api/bff/platform-ai/[...path]/route.ts`
- `apps/web/src/app/api/bff/policy/[...path]/route.ts`
- Identity BFF already exists — confirm admin paths passthrough
- merchant-teams BFF exists — confirm admin merchants path
- `.env.example` URLs (evals `:8031`, observability `:8033`, platform-ai `:8036`, policy per README)

- [ ] **Steps: tests for 401 without session, check, commit** `feat(web): admin peer BFF proxies`

---

### Task 6: Wire all admin stub pages

**Files:** Replace stubs under `apps/web/src/app/admin/(protected)/{roles,tenants,teams,policies,security,integrations,merchants,ai,evaluations,observability,audit}/page.tsx`

**Interfaces:**

- Shared panel component(s) OK: fetch via BFF, render table/list, `peer-error`, `data-testid` matching existing (`admin-roles`, etc.)
- Never “Not available yet”
- Browser tests covering ≥1 page per peer family + peer-error

- [ ] **Steps: TDD, `make -C apps/web check`, commit** `feat(web): admin remainder pages from peers`

---

### Task 7: verify-wave5 + program index

**Files:** integration/core verify-wave5, seed hooks if needed, sandbox-matrix, program index Wave 5 → done

**Assert:** identity admin roles/tenants; policy policies; merchants; platform-ai config/integrations; evals reports; observability signals (with admin/sandbox tokens as documented)

- [x] **Steps: check, commit** `feat(integration): wave 5 admin verify`

---

## Execution notes

- Tasks 1–4 parallel OK (different roots).
- Users page already wired — do not regress.
- Wave 6 money-path E2E is separate.
