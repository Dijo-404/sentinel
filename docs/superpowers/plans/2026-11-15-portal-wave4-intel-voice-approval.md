# Portal Wave 4: Intel peers + voice + real approval-ui

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship DB-backed assistant / knowledge / ops-activity / platform-ai peers; extend evals/core HTTP+DB and add services/observability; wire real `packages/approval-ui` and `services/voice` into the portal real-peers path; replace operator Activity/Knowledge/Assistant and customer Assistant stubs.

**Architecture:** New FastAPI+Postgres services under `services/` with session BFF proxies. Assistant persists threads/messages only (no ledger decide). Knowledge is articles/search. Ops-activity is a feed (case-event projection and/or local rows). Platform-ai stores admin AI config metadata only. Evals remain `evals/core` authority with optional HTTP serve. Observability is new HTTP+DB query service using `packages/telemetry` types. Web mounts SN-013 `ApprovalPanel` when `real-peers`; voice slot enabled with BFF → voice peer (Sarvam opt-in server-side).

**Tech Stack:** FastAPI, PostgreSQL, Next.js BFF, React (`packages/approval-ui`), Vitest/pytest, uv.

**Spec:** `docs/superpowers/specs/2026-11-15-portal-db-backed-completion-design.md` (Wave 4)

## Global Constraints

- Contract: `sentinel.task-contracts.v1` / SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`
- Product: `NEXT_PUBLIC_SHELL_MODE=real-peers`; no silent fixture rows
- Ports: assistant `8026`, knowledge `8035` (8034 = merchant-teams; 8028 = merchant-inbox), ops-activity `8029`, platform-ai `8036` (8030 = merchant-disputes), evals HTTP `8031`, analytics `8032`, observability `8033`, voice `8017` (existing)
- Assistants/knowledge/voice/platform-ai **never** call ledger decide or mint refunds
- Sarvam secrets only in ignored `services/voice/.env`; `make check` credential-free
- Worktree: `/home/dj/projects/sentinel-portal-wave0-1` · branch `feat/portal-wave4-intel-voice-approval`
- Commit per task; no push/`main` unless user asks

## Review Focus

- Real-peers approval path uses `ApprovalPanel` from `@sentinel/approval-ui` (or workspace package name) — not `LocalApprovalSubstitute`
- Voice disabled → visible disabled slot; enabled + peer down → peer-error, not fake live transcript
- Assistant message create persists to DB; empty thread is honest `[]`
- New services refuse seed outside `tenant-demo` / sandbox
- Eval HTTP does not invent a second `evaluation.v1` owner

## Out of scope (Wave 5+)

- Full admin Roles/Tenants/Policies/Security/Integrations/Merchants page wiring (Wave 5 may consume platform-ai/evals/obs APIs built here)
- Money-path E2E assembly journeys (Wave 6)

---

### Task 1: `services/assistant` HTTP+Postgres scaffold + seed

**Files:** Create owned root `services/assistant/` (pyproject, Makefile, README, CHANGELOG, migrations, src, tests, contracts/assistant.v1.json)

**Interfaces:**

- `GET /v1/health`, `GET /v1/capabilities`
- `GET /v1/threads?role=customer|operator` → `{ threads: [{ thread_id, title, updated_at }] }`
- `POST /v1/threads` `{ title? }` → thread
- `GET /v1/threads/{id}/messages` → `{ messages: [{ message_id, role, text, evidence_mode, created_at }] }`
- `POST /v1/threads/{id}/messages` `{ text }` → message with `evidence_mode: "sandbox"` (no model money authority; optional stub reply message labeled sandbox)
- Auth: Bearer principal; tenant from token map / identity session projection pattern used by peers
- Port default `8026`; `make seed` ≥1 thread + message for `tenant-demo`

- [ ] **Steps: TDD, `make -C services/assistant check` PASS, commit** `feat(assistant): http+postgres threads`

---

### Task 2: `services/knowledge` HTTP+Postgres + seed

**Files:** `services/knowledge/` mirror Task 1 shape

**Interfaces:**

- `GET /v1/articles` → `{ articles: [{ article_id, title, summary, updated_at }] }`
- `GET /v1/articles/{id}` → article body
- `GET /v1/search?q=` → `{ hits: [...] }` (simple ILIKE/title match OK)
- Port `8035`; seed ≥1 article for sandbox

- [ ] **Steps: TDD, check, commit** `feat(knowledge): http+postgres articles`

---

### Task 3: `services/ops-activity` HTTP+Postgres + seed

**Files:** `services/ops-activity/`

**Interfaces:**

- `GET /v1/activity` → `{ items: [{ activity_id, kind, summary, occurred_at, case_id? }] }` newest first max 50
- May insert seed rows; optional later projection from case-api (document if sync stub)
- Port `8029`

- [ ] **Steps: TDD, check, commit** `feat(ops-activity): activity feed`

---

### Task 4: `services/platform-ai` HTTP+Postgres + seed

**Files:** `services/platform-ai/`

**Interfaces:**

- `GET /v1/config` → `{ models: [...], kill_switch: bool, updated_at }`
- `GET /v1/runs` → `{ runs: [{ run_id, model_id, status, started_at }] }` (metadata only)
- Port `8036`; no money fields; seed one config row + one run

- [ ] **Steps: TDD, check, commit** `feat(platform-ai): config and run metadata`

---

### Task 5: `evals/core` Postgres report store + HTTP serve

**Files:** under `evals/core/` — store adapter, migration, ASGI/preview entry, tests

**Interfaces:**

- Persist `RunReport` rows; `GET /v1/reports`, `GET /v1/reports/{id}`
- Port `8031` via `make preview-http` or documented preview
- CLI/CI runner unchanged as authority; HTTP reads same store
- Seed one synthetic report for sandbox

- [ ] **Steps: TDD, `make -C evals/core check` PASS, commit** `feat(evals): http+postgres run reports`

---

### Task 6: `services/observability` HTTP+DB ingest/query

**Files:** `services/observability/` using types from `packages/telemetry` (Python port or JSON schema alignment — prefer import/copy of wire shapes without forking contract)

**Interfaces:**

- `POST /v1/ingest` (sandbox) / `GET /v1/signals` or `/v1/spans` list for admin
- Port `8033`; seed ≥1 signal; never claim financial audit

- [ ] **Steps: TDD, check, commit** `feat(observability): http+db query service`

---

### Task 7: Web BFF + operator/customer intel pages

**Files:**

- BFF routes: `apps/web/src/app/api/bff/assistant|knowledge|ops-activity/[...path]/route.ts`
- Replace stubs: operator `activity`, `knowledge`, `assistant`; customer `assistant`
- Panels + browser tests; `data-testid` + `peer-error`
- `.env.example` base URLs; CHANGELOG

- [ ] **Steps: TDD, `make -C apps/web check`, commit** `feat(web): assistant knowledge activity from peers`

---

### Task 8: Real `packages/approval-ui` in real-peers

**Files:**

- `apps/web/src/slots/approval-slot.tsx` — import `ApprovalPanel` from approval-ui package when mode real-peers (or always prefer package; fixture may keep substitute)
- Workspace dependency: add `packages/approval-ui` to web package.json if needed
- Map `ApprovalSlotProps` → `ApprovalPanel` props + decide client via case-api BFF
- Tests: real-peers path does not render `data-slot` local substitute; fixture may
- COMPATIBILITY.md / CHANGELOG

- [ ] **Steps: TDD, check, commit** `feat(web): mount SN-013 approval-ui in real-peers`

---

### Task 9: Voice on — BFF + composition + intake wiring

**Files:**

- BFF `apps/web/src/app/api/bff/voice/[...path]/route.ts`
- Real peer voice client; `NEXT_PUBLIC_VOICE_ENABLED=true` in `.env.example` for product demo
- Wire voice slot on intake (or documented portal surface already prepared)
- Fail visible when peer down; label `evidence_mode` recorded vs live
- Tests without SARVAM key

- [ ] **Steps: TDD, check, commit** `feat(web): enable voice slot via voice peer`

---

### Task 10: Sandbox seed hooks + verify-wave4

**Files:**

- Wire `seed-sandbox` to new peers + evals/obs
- `integration/core` verify-wave4: health/list endpoints for assistant/knowledge/activity; approval package import smoke; voice capabilities
- Update `sandbox-matrix.md` ports
- Program index Wave 4 → done

- [x] **Steps: check, commit** `feat(integration): wave 4 intel voice verify`

---

## Execution notes

- Tasks 1–4 (+5–6) are independent owned roots — parallel implementers OK if no shared file edits.
- Thin service scaffold may copy patterns from `services/merchant-inbox` / `services/risk` (Postgres + bearer).
- Admin AI/Evaluations/Observability **pages** remain Wave 5; Wave 4 only needs APIs + seed so Wave 5 is thin UI.
- After Task 10: push/PR when user asks (or continue prior merge habit if instructed).
