# Portal Wave 0–1: Foundation + Merchant/Risk DB-backed pages

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run a real-peers sandbox seed path and replace merchant Analytics/Disputes/Exceptions/Tasks/Team plus all risk stub pages with UI that loads only from BFF → peer → DB (or fails closed).

**Architecture:** Shared sandbox seed writes synthetic rows into each peer’s Postgres. Web stays on port 3012 with `NEXT_PUBLIC_SHELL_MODE=real-peers` and session BFF proxies. Merchant/risk pages stop rendering stub copy; they call existing or extended peer APIs. No client-invented demo tables.

**Tech Stack:** Next.js BFF (`apps/web`), FastAPI peers (`services/merchant-*`, `services/risk`), PostgreSQL, uv/Make, Vitest/pytest.

**Spec:** `docs/superpowers/specs/2026-11-15-portal-db-backed-completion-design.md`

## Global Constraints

- Contract: `sentinel.task-contracts.v1` / SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`
- Mode for product demo: `real-peers`; fixture only inside module `make check`
- No secrets in `NEXT_PUBLIC_*`; BFF forwards `sentinel_session`
- Never silent fixture fallback in real-peers
- Work only in claimed owned roots; feature branch + worktree; no push/`main` merge
- Sandbox tenant `tenant-demo` only for seed tools
- Commit on the feature branch when the task says so (user authorized implementation)

## Review Focus

- Peer down / empty DB → page shows explicit error or honest empty list from API, never hard-coded rows
- Session missing → BFF 401, not stub success
- Seed refuses non-`tenant-demo` / non-sandbox
- Merchant metrics/disputes scoped to merchant principal (no cross-tenant leak)
- Risk pages never expose ledger decide controls

---

### Task 1: Sandbox seed harness (integration/core)

**Files:**
- Create: `integration/core/scripts/seed_sandbox.py` (or module CLI entry already patterned in repo)
- Create: `integration/core/tests/test_seed_sandbox_gate.py`
- Modify: `integration/core/Makefile` (add `seed-sandbox` target)
- Modify: `integration/core/README.md`, `integration/core/CHANGELOG.md`
- Modify: `integration/core/docs/sandbox-matrix.md` (document seed command + DB names)

**Interfaces:**
- Consumes: sandbox matrix tokens/URLs from `integration/core/fixtures/sandbox-assembly.json` / `sandbox-tokens.json`
- Produces: `seed_sandbox(env: Mapping[str, str]) -> SeedReport` where `SeedReport = { status: "PASS"|"FAIL", seeds: list[{peer, rows}], reason_code?: str }`; refuses unless `CORE_ASSEMBLY_TENANT_ID=tenant-demo` and sandbox flag true

- [ ] **Step 1: Write failing test** `test_seed_refuses_non_demo_tenant` asserting `reason_code == "SANDBOX_TENANT_REQUIRED"` when tenant ≠ `tenant-demo`

- [ ] **Step 2: Run test — expect FAIL** (entry missing)

Run: `make -C integration/core check` or targeted pytest for the new test  
Expected: FAIL

- [ ] **Step 3: Implement seed gate + no-op/PASS report for peers not yet migrated (document skips); wire Makefile `seed-sandbox`**

- [ ] **Step 4: Run test — expect PASS**

- [ ] **Step 5: Commit on feature branch in worktree** `feat/portal-wave0-seed` (or claimed issue branch)

```bash
git commit -m "feat(integration): sandbox seed gate for tenant-demo"
```

---

### Task 2: Merchant-analytics Postgres snapshot store

**Files:**
- Create/Modify under `services/merchant-analytics/`: schema/migration or SQLAlchemy metadata for `merchant_metrics_snapshots`
- Modify: storage adapter + bootstrap to prefer `MERCHANT_ANALYTICS_DATABASE_URL` in real-peers
- Create: `make seed` writing one snapshot for `merchant-demo-1` / matrix window
- Test: `services/merchant-analytics/tests/test_metrics_from_db.py`
- Update README/CHANGELOG/`.env.example`

**Interfaces:**
- Consumes: existing `GET /v1/merchants/{merchant_ref}/metrics`
- Produces: same JSON from DB row when present; `404`/`503` with clear code when missing/DB down (no in-memory fake metrics in real-peers)

- [ ] **Step 1: Failing test** `test_metrics_served_from_postgres_snapshot` — insert row, GET metrics, assert values match DB not fixture aggregate invention

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement DB snapshot read path + seed**

- [ ] **Step 4: `make -C services/merchant-analytics check` PASS**

- [ ] **Step 5: Commit** `feat(merchant-analytics): postgres metrics snapshots`

---

### Task 3: Web merchant Analytics page (real BFF)

**Files:**
- Modify: `apps/web/src/app/merchant/(protected)/analytics/page.tsx`
- Create: `apps/web/src/components/merchant/analytics-panel.tsx` (client fetch via `/api/bff/merchant-analytics/...`)
- Create: `apps/web/tests/.../merchant-analytics-page.test.tsx`
- Modify: `.env.example` note real-peers requires `MERCHANT_ANALYTICS_BASE_URL`
- Update `apps/web/CHANGELOG.md`

**Interfaces:**
- Consumes: existing BFF `apps/web/src/app/api/bff/merchant-analytics/[...path]/route.ts`
- Produces: page `data-testid="merchant-analytics"` showing metrics from fetch OR error banner `data-testid="peer-error"`; never “Not available yet”

- [ ] **Step 1: Failing test** asserts stub copy absent and peer-error or metrics region present when fetch mocked

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement panel + page**

- [ ] **Step 4: `make -C apps/web check` (or focused vitest) PASS**

- [ ] **Step 5: Commit** `feat(web): merchant analytics from BFF`

---

### Task 4: Merchant-disputes Postgres + seed

**Files:**
- Under `services/merchant-disputes/`: add Postgres adapter (or promote sqlite path to Postgres DSN), migration, `make seed` for one OPEN dispute on `tenant-demo`
- Tests for list/get from DB
- README/CHANGELOG/`.env.example`

**Interfaces:**
- Produces: `GET` list/detail routes already in service (or add `GET /v1/merchants/{ref}/disputes` if missing — prefer existing routes; document exact path in README)

- [ ] **Step 1: Failing DB persistence test**

- [ ] **Step 2–4: Implement, check PASS, commit** `feat(merchant-disputes): postgres + seed`

---

### Task 5: Web merchant Disputes + Exceptions + Tasks pages

**Files:**
- Replace stubs: `apps/web/src/app/merchant/(protected)/disputes/page.tsx`, `exceptions/page.tsx`, `tasks/page.tsx`
- BFF: add `apps/web/src/app/api/bff/merchant-disputes/[...path]/route.ts` if missing (mirror `_session-proxy.ts` pattern)
- Exceptions/Tasks: map to merchant-inbox and/or case-api queue endpoints already available; if inbox has no HTTP list yet, extend `services/merchant-inbox` in this task’s ownership only after claiming — else read case-api ops list filtered for merchant (document ruling in PR)
- Tests for each page: no stub copy; empty/error from API OK

**Interfaces:**
- Consumes: disputes peer + inbox/case-api as chosen
- Produces: `data-testid` `merchant-disputes` | `merchant-exceptions` | `merchant-tasks`

- [ ] **Steps: TDD each page, `make -C apps/web check`, commit** `feat(web): merchant disputes exceptions tasks from peers`

---

### Task 6: Merchant Team page via merchant-teams

**Files:**
- `services/merchant-teams`: ensure Postgres + seed membership for `merchant-demo-1` if not present
- BFF `merchant-teams` proxy if missing
- Replace `apps/web/src/app/merchant/(protected)/team/page.tsx`
- Tests + changelog

- [ ] **Steps: TDD, check, commit** `feat(web): merchant team from merchant-teams peer`

---

### Task 7: Merchant Settings page (DB-backed)

**Files:**
- Prefer thin settings resource on `services/merchant-teams` or existing merchant service (builder picks thinner; record in README)
- Web `settings/page.tsx` + BFF
- Seed one settings row; GET returns it

- [ ] **Steps: TDD, check, commit**

---

### Task 8: Risk service Postgres seed + list endpoints

**Files:**
- `services/risk`: enable `RISK_DATABASE_URL` path; `make seed` creates investigation + restriction + findings for `case-demo-42`
- Ensure list routes cover queue/holds/transactions/reports/analytics/audit needs (add read models only if missing)
- Tests + README/CHANGELOG

**Interfaces:**
- Existing risk routes from README; extend only with versioned additive GETs if required for portal columns

- [ ] **Steps: TDD seed+lists, `make -C services/risk check`, commit**

---

### Task 9: Web risk stub pages → BFF risk

**Files:**
- Replace stubs under `apps/web/src/app/risk/(protected)/{queue,holds,audit,analytics,reports,transactions}/page.tsx`
- Use existing `apps/web/src/app/api/bff/risk/[...path]/route.ts`
- Shared `RiskPeerPanel` component OK if thin
- Tests: no “Not available yet”; peer-error on 503

- [ ] **Steps: TDD, `make -C apps/web check`, commit** `feat(web): risk portal pages from BFF`

---

### Task 10: Remove invented merchant/customer fixture transaction tables (real-peers honesty)

**Files:**
- `apps/web/src/app/merchant/(protected)/transactions/page.tsx`
- `apps/web/src/app/merchant/(protected)/refunds/page.tsx`
- `apps/web/src/app/customer/(protected)/transactions/page.tsx`
- Wire to settlement/refunds/case-api DB peers or fail closed with peer-error (no hard-coded demo rows in real-peers)
- Fixture mode may keep labeled stub **only** if `config.mode === "fixture"` and banner says fixture — product demo uses real-peers

- [ ] **Steps: TDD mode split, check, commit** `fix(web): no invented rows in real-peers lists`

---

### Task 11: Wave 0–1 verification script

**Files:**
- Create: `integration/core/scripts/verify_wave0_1.sh` (or pytest) hitting analytics/disputes/risk BFF paths against seeded stack OR documenting manual curl checklist in README if full compose not yet automated
- Must assert HTTP 200 + JSON from DB-backed peers for at least analytics metrics + one risk list + one dispute list

- [ ] **Step 1: Write verification that fails without seed**
- [ ] **Step 2: Document run order in integration README**
- [ ] **Step 3: Commit**

---

## Execution note

After Task 11, write Wave 2 plan file and continue SDD. Do not expand into assistant/knowledge/voice/approval-ui in this plan.
