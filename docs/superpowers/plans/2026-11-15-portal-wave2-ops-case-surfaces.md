# Portal Wave 2: Ops case surfaces (escalations, messages, history, audit, team)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace operator Escalations/Messages and supervisor Escalations/History/Audit/Team stubs with pages that load only from BFF → case-api / identity → Postgres (or fail closed).

**Architecture:** Extend case-api read projections for ops lists (escalations reuse `GET /v1/ops/cases?status=ESCALATED`; add messages inbox + audit event feed + history filter for terminal statuses). Supervisor Team lists ops principals via identity admin users (existing `GET /v1/admin/users`) through a new web identity BFF. No new case authority; no ledger decide from these pages.

**Tech Stack:** Next.js BFF (`apps/web`), FastAPI case-api (`apps/api`), identity (`services/identity`), PostgreSQL, Vitest/pytest.

**Spec:** `docs/superpowers/specs/2026-11-15-portal-db-backed-completion-design.md` (Wave 2 row)

## Global Constraints

- Contract baseline: `sentinel.task-contracts.v1` / SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`
- Product mode: `NEXT_PUBLIC_SHELL_MODE=real-peers`; fixture only inside module checks
- No UI mock/fixture product rows; seed Postgres; fail closed when peer/DB down
- No secrets in `NEXT_PUBLIC_*`; BFF forwards `sentinel_session`
- SN-009 sole money authority — these pages never call decide/refund
- Worktree: `/home/dj/projects/sentinel-portal-wave0-1` on `feat/portal-wave0-1-foundation` (or claimed issue branch); no push/`main` merge
- Sandbox tenant `tenant-demo` only for seed
- Commit on feature branch when each task says so

## Review Focus

- Peer down / empty DB → `data-testid="peer-error"` or honest empty list from API, never hard-coded rows
- Session missing → BFF 401
- Escalations/history/messages/audit scoped to principal tenant (no cross-tenant leak)
- Team page never invents staff; identity 403/503 → peer-error
- Operator Messages page never posts without case_id; list is read projection
- Pages never render “Not available yet”

## Out of scope (later waves)

- Operator Activity / Knowledge / Assistant (Wave 4 intel peers)
- Real `packages/approval-ui` + voice (Wave 4)
- Admin remainder, money-path E2E (Waves 5–6)

---

### Task 1: Case-api ops messages inbox + history + audit projections

**Files:**

- Modify: `apps/api/src/sentinel_api/adapters/http/app.py`
- Modify: `apps/api/src/sentinel_api/application/service.py`
- Modify: `apps/api/src/sentinel_api/application/ports.py`
- Modify: `apps/api/src/sentinel_api/adapters/db/repository.py` (and schema only if a query index is required)
- Create: `apps/api/tests/integration/test_ops_projections.py`
- Modify: `apps/api/CHANGELOG.md`, `apps/api/README.md`

**Interfaces:**

- Consumes: existing `list_queue` / case_messages / case_events tables
- Produces:
  - `GET /v1/ops/cases?status=ESCALATED` — already works; seed must leave ≥1 ESCALATED row (covered in Task 2)
  - `GET /v1/ops/cases?status=VERIFIED_RESOLVED` and `?status=CLOSED_NO_ACTION` — history pages may call twice or use comma filter
  - Prefer additive: `GET /v1/ops/cases?status=HISTORY` where HISTORY = statuses in `{VERIFIED_RESOLVED, CLOSED_NO_ACTION}` (document exact enum in README)
  - `GET /v1/ops/messages` → `{ "messages": [ { "case_id", "message_id", "text", "language", "author", "occurred_at" } ], "next_cursor"?: string }` — tenant-scoped, newest first, max 50
  - `GET /v1/ops/audit-events` → `{ "events": [ { "case_id", "sequence", "type", "occurred_at", "payload" } ], "next_cursor"?: string }` — tenant-scoped case events, newest first, max 50; redact secrets already in event writer rules
- Roles: operator + supervisor (same as `list_queue`); customer → 403

- [ ] **Step 1: Write failing tests** `test_ops_messages_lists_seeded_message`, `test_ops_history_status_filter`, `test_ops_audit_events_lists_seeded_event`, `test_ops_projections_forbid_customer`

- [ ] **Step 2: Run** `cd apps/api && uv run pytest tests/integration/test_ops_projections.py -v` — expect FAIL

- [ ] **Step 3: Implement repository queries + service + HTTP routes; wire HISTORY status alias**

- [ ] **Step 4: `make -C apps/api check` PASS**

- [ ] **Step 5: Commit** `feat(api): ops messages history audit projections`

---

### Task 2: Case-api seed rows for escalations / messages / history / audit

**Files:**

- Modify: case-api seed path used by wave verify (`apps/api` Makefile `seed` and/or `integration/core` seed hooks)
- Modify: `apps/api/tests/...` asserting seed shapes if seed is module-local
- Modify: `apps/api/README.md`, `integration/core/docs/sandbox-matrix.md` if ports/commands change
- Modify: `apps/api/CHANGELOG.md`

**Interfaces:**

- For `tenant-demo`, after seed:
  - ≥1 case with `status=ESCALATED`
  - ≥1 case message visible via `GET /v1/ops/messages`
  - ≥1 case with HISTORY status (`VERIFIED_RESOLVED` or `CLOSED_NO_ACTION`)
  - ≥1 case event visible via `GET /v1/ops/audit-events`
- Refuse seed unless sandbox/`tenant-demo` (reuse existing gate)

- [ ] **Step 1: Failing test** `test_seed_ops_surfaces_present` (or extend verify fixture)

- [ ] **Step 2: Implement seed mutations / inserts**

- [ ] **Step 3: `make -C apps/api check` PASS; document `make seed`**

- [ ] **Step 4: Commit** `feat(api): seed ops escalations messages history audit`

---

### Task 3: Web CaseClient + BFF paths for new ops GETs

**Files:**

- Modify: `apps/web/src/application/ports.ts` — add `listOpsMessages()`, `listOpsAuditEvents()`, document HISTORY on `listOpsCases`
- Modify: `apps/web/src/adapters/real-peer-case-client.ts`, `bff-case-client.ts` (if thin wrapper), fixture stub `tests/stubs/case-api/index.ts`
- Modify: existing BFF `apps/web/src/app/api/bff/case/[...path]/route.ts` (proxy already covers `/v1/ops/**` if path-passthrough — verify; extend only if allowlist blocks)
- Create/Modify: `apps/web/tests/peer-clients.test.ts` or unit stub tests
- Modify: `apps/web/CHANGELOG.md`

**Interfaces:**

- `listOpsMessages(): Promise<{ messages: OpsMessage[] }>`
- `listOpsAuditEvents(): Promise<{ events: OpsAuditEvent[] }>`
- `listOpsCases({ status: "ESCALATED" | "HISTORY" | ... })` unchanged signature; stub returns seeded shapes in fixture mode only

- [ ] **Step 1: Failing client tests for path + JSON shape**

- [ ] **Step 2: Implement adapters + stub**

- [ ] **Step 3: `make -C apps/web check` PASS**

- [ ] **Step 4: Commit** `feat(web): case client ops messages audit history`

---

### Task 4: Operator Escalations + Messages pages

**Files:**

- Replace: `apps/web/src/app/operator/(protected)/escalations/page.tsx`
- Replace: `apps/web/src/app/operator/(protected)/messages/page.tsx`
- Create: `apps/web/src/components/ops/escalations-panel.tsx`
- Create: `apps/web/src/components/ops/messages-panel.tsx`
- Create: `apps/web/tests/browser/operator-escalations-messages.test.tsx`
- Modify: `apps/web/CHANGELOG.md`

**Interfaces:**

- Escalations: `listOpsCases({ status: "ESCALATED" })` via browser case client / BFF; `data-testid="operator-escalations"`; rows link to `/operator/cases/{caseId}`; peer failure → `data-testid="peer-error"`; never “Not available yet”
- Messages: `listOpsMessages()`; `data-testid="operator-messages"`; show case_id + text + occurred_at; empty `[]` OK; peer-error on failure

- [ ] **Step 1: Failing browser tests** (stub copy absent; peer-error or list region)

- [ ] **Step 2: Implement panels + pages**

- [ ] **Step 3: `make -C apps/web check` PASS**

- [ ] **Step 4: Commit** `feat(web): operator escalations and messages from case-api`

---

### Task 5: Supervisor Escalations + History + Audit pages

**Files:**

- Replace: `apps/web/src/app/supervisor/(protected)/escalations/page.tsx`
- Replace: `apps/web/src/app/supervisor/(protected)/history/page.tsx`
- Replace: `apps/web/src/app/supervisor/(protected)/audit/page.tsx`
- Create: `apps/web/src/components/ops/supervisor-escalations-panel.tsx` (or reuse shared escalations panel with role base path)
- Create: `apps/web/src/components/ops/history-panel.tsx`
- Create: `apps/web/src/components/ops/audit-panel.tsx`
- Create: `apps/web/tests/browser/supervisor-ops-surfaces.test.tsx`
- Modify: `apps/web/CHANGELOG.md`

**Interfaces:**

- Escalations: same API as operator; links to `/supervisor/cases/{caseId}`; `data-testid="supervisor-escalations"`
- History: `listOpsCases({ status: "HISTORY" })`; `data-testid="supervisor-history"`
- Audit: `listOpsAuditEvents()`; `data-testid="supervisor-audit"`; display type/case_id/occurred_at; no decide controls
- All: peer-error fail closed

- [ ] **Step 1: Failing browser tests**

- [ ] **Step 2: Implement**

- [ ] **Step 3: `make -C apps/web check` PASS**

- [ ] **Step 4: Commit** `feat(web): supervisor escalations history audit from case-api`

---

### Task 6: Supervisor Team via identity admin users + BFF

**Files:**

- Create: `apps/web/src/app/api/bff/identity/[...path]/route.ts` (mirror `_session-proxy.ts` pattern; upstream `IDENTITY_BASE_URL`)
- Create: `apps/web/src/lib/server/identity-bff.ts` or thin fetch helper if needed
- Replace: `apps/web/src/app/supervisor/(protected)/team/page.tsx`
- Create: `apps/web/src/components/ops/team-panel.tsx`
- Create: `apps/web/tests/browser/supervisor-team-page.test.tsx`
- Modify: `apps/web/.env.example` (`IDENTITY_BASE_URL`)
- Modify: `apps/web/CHANGELOG.md`
- If identity lacks a supervisor-safe list: add additive `GET /v1/ops/team` on identity **or** document that supervisor session may call existing `GET /v1/admin/users` only when role permits — prefer extending identity with `GET /v1/tenants/me/assignments?role=operator,supervisor` read for supervisor without full admin. Record ruling in README.
- Owned roots: `apps/web` always; `services/identity` only if endpoint missing (claim/coordinate)

**Interfaces:**

- Page `data-testid="supervisor-team"` lists `{ user_id or principal_id, email or display, role }[]` from peer
- Fail closed `peer-error`; never invent roster
- Fixture mode: local stub roster labeled fixture **only** when `SHELL_MODE=fixture`

- [ ] **Step 1: Failing browser test**

- [ ] **Step 2: Implement BFF + page; add identity list endpoint only if required**

- [ ] **Step 3: `make -C apps/web check` (+ `make -C services/identity check` if touched) PASS**

- [ ] **Step 4: Commit** `feat(web): supervisor team from identity`

---

### Task 7: Wave 2 verify hook

**Files:**

- Create/Modify: `integration/core/src/sentinel_core_assembly/adapters/verify_wave2.py` or extend `verify_wave0_1.py` with wave2 section
- Create: `integration/core/scripts/verify-wave2.sh` (or Makefile target `verify-wave2`)
- Modify: `integration/core/README.md`, `CHANGELOG.md`
- Assert against seeded stack (or document curl checklist if compose not up): HTTP 200 JSON for ops messages, audit-events, HISTORY list, ESCALATED list; web pages not required in script if BFF needs session — then assert case-api + identity directly with matrix tokens

- [x] **Step 1: Write verify that fails without seed rows**

- [x] **Step 2: Document run order**

- [x] **Step 3: Commit** `feat(integration): wave 2 ops surfaces verify`

---

## Execution notes

- Prefer shared `EscalationsPanel` parameterized by `basePath: "/operator" | "/supervisor"` to avoid duplicate UI.
- Do not scaffold assistant/knowledge/ops-activity here.
- Marketing landing simulated preview stays labeled; out of scope.
- After Task 7: mark program index Wave 2 complete; open PR only if user asks.
