# Mercury web shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild `apps/web` UI as a Mercury night landing, shared `/login`, night sidebar shell, and rich viz dashboards for merchant, operator, and supervisor.

**Architecture:** CSS design tokens + Framer Motion marketing/shell chrome in `apps/web` only. Shared viz primitives feed three role dashboards. Auth/BFF/ports unchanged; fixture metrics labeled simulator. Track A lands first; B/C/D dashboards parallel after shell ships.

**Tech Stack:** Next.js 15, React 19, Framer Motion, Recharts, Inter (Google font), existing fixture identity + case-api stubs.

**Spec:** `docs/superpowers/specs/2026-11-14-mercury-web-shell-design.md`

**Worktree:** `.worktrees/feat-sn-012-mercury-ui` on branch `feat/sn-012-mercury-ui`

## Global Constraints

- Edit only `apps/web/**` plus this plan/spec under `docs/superpowers/**` if needed for handoff notes.
- Preserve financial hard lines: no second ledger, no amount edits, no client-minted digests, no silent fixture fallback in real-peers.
- Keep `data-testid`s: `portal-entry` (landing may keep or add `landing-page`), `role-login`, `login-email`, `login-password`, `logout`, `{role}-dashboard`, approval tests unchanged in behavior.
- Primary solid CTA color `#5266eb` once per CTA group; type weights ≤ 500.
- Fixture banners on all synthetic metrics.
- `make -C apps/web check` must pass after each task group.
- Commits on `feat/sn-012-mercury-ui` only; no push/merge unless human asks.

## Review Focus

1. Reduced motion: landing still readable with motion disabled.
2. Signed-in `/`: marketing stays; nav shows Dashboard not Log in.
3. Operator never sees approval controls on queue/evidence.
4. Supervisor decide payload still exact digest/revision/expiry/policy.
5. Real-peer peer errors remain visible (no silent stub swap).

---

### Task 1: Design tokens, deps, app chrome base

**Files:**
- Modify: `apps/web/package.json`, `apps/web/package-lock.json`
- Modify: `apps/web/src/app/globals.css`, `apps/web/src/app/layout.tsx`
- Test: `apps/web/tests/browser/shell.test.tsx` (smoke still loads)

**Interfaces:**
- Produces: CSS vars `--night`, `--night-raised`, `--canvas`, `--surface`, `--lavender`, `--primary`, `--ink`, `--ink-secondary`, `--on-dark`, `--fog`, `--periwinkle`; font Inter; deps `framer-motion`, `recharts`

- [ ] **Step 1:** Add `framer-motion` and `recharts` via npm in `apps/web`; Inter via `next/font/google` in `layout.tsx`.
- [ ] **Step 2:** Replace graphite token block in `globals.css` with Mercury tokens; keep status chip vars for domain states.
- [ ] **Step 3:** Run `make -C apps/web check` — expect PASS (or fix type-only breaks).
- [ ] **Step 4:** Commit `feat(web): add Mercury tokens and motion/chart deps`

---

### Task 2: App shell + shared login + landing

**Files:**
- Create: `apps/web/src/components/shell/app-sidebar.tsx`, `apps/web/src/components/marketing/landing-page.tsx`, `apps/web/src/components/marketing/hero-stage.tsx`
- Modify: `apps/web/src/components/layout/protected-shell.tsx`
- Modify: `apps/web/src/components/auth/role-login.tsx`
- Create: `apps/web/src/app/login/page.tsx`
- Modify: `apps/web/src/app/page.tsx`
- Modify: each `apps/web/src/app/{role}/login/page.tsx` → redirect to `/login?portal={role}`
- Modify: `apps/web/tests/browser/auth-portals.test.tsx` as needed for `/login`

**Interfaces:**
- Consumes: `PORTAL_NAV`, `logoutAction`, `loginAction`, `getSession`/`requireRole` helpers if available for signed-in nav
- Produces: `ProtectedShell` with night sidebar; `LandingPage`; `/login` with workspace select setting hidden `role`

- [ ] **Step 1:** Test `landing shows Get started linking to /login` and `shared login has workspace select and role-login testid`.
- [ ] **Step 2:** Implement landing (night nav, hero, stats, bento, quote, footer, Framer load sequence; reduced-motion safe). CTA **Get started** → `/login`. Signed-in: Dashboard link via server session read on page.
- [ ] **Step 3:** Implement `/login` wrapping `RoleLogin` with workspace `<select name="role">` (required). Redirect old role logins.
- [ ] **Step 4:** Rebuild `ProtectedShell` as sidebar + canvas main; preserve `data-portal`, `logout` testid, nav from props.
- [ ] **Step 5:** `make -C apps/web check` PASS; commit `feat(web): Mercury landing, shared login, sidebar shell`

---

### Task 3: Viz primitives

**Files:**
- Create: `apps/web/src/components/viz/stat-block.tsx`, `trend-pill.tsx`, `chart-card.tsx`, `fixture-banner.tsx`
- Create: `apps/web/src/components/viz/fixture-series.ts` (typed synthetic series helpers)
- Test: `apps/web/tests/browser/viz-primitives.test.tsx`

**Interfaces:**
- Produces: `StatBlock({ label, value, caption? })`, `TrendPill({ value, direction })`, `ChartCard({ title, children })`, `FixtureBanner`, `fixtureSeries.*` returning number arrays / `{x,y}[]`

- [ ] **Step 1:** Test renders StatBlock + FixtureBanner with simulator copy.
- [ ] **Step 2:** Implement primitives (lavender/night-raised cards, no heavy shadows).
- [ ] **Step 3:** Check + commit `feat(web): shared viz primitives`

---

### Task 4: Merchant dashboard viz (parallel-ready)

**Files:**
- Modify: `apps/web/src/app/merchant/(protected)/dashboard/page.tsx`
- Create: `apps/web/src/components/dashboards/merchant-overview.tsx`
- Test: assert `merchant-dashboard` + fixture banner + ≥3 KPI labels

**Interfaces:**
- Consumes: viz primitives, `session`
- Produces: merchant overview with volume/exceptions/refund-requests KPIs + Recharts area (fixture series)

- [ ] Implement + test + `make -C apps/web check` + commit `feat(web): merchant overview viz`

---

### Task 5: Operator dashboard + queue wire (parallel-ready)

**Files:**
- Modify: `apps/web/src/app/operator/(protected)/dashboard/page.tsx`
- Modify: `apps/web/src/app/operator/(protected)/queue/page.tsx`
- Create: `apps/web/src/components/dashboards/operator-overview.tsx`
- Reuse: `apps/web/src/components/operator-queue.tsx`

**Interfaces:**
- Consumes: `getCaseClient` / composition same as `/ops`, viz primitives
- Produces: KPIs + status chart from `listOpsCases()` when available else fixture; `/operator/queue` renders `OperatorQueue`

- [ ] Wire queue page to `OperatorQueue` (no approval).
- [ ] Dashboard overview + tests; check; commit `feat(web): operator overview and queue`

---

### Task 6: Supervisor dashboard viz (parallel-ready)

**Files:**
- Modify: `apps/web/src/app/supervisor/(protected)/dashboard/page.tsx`
- Create: `apps/web/src/components/dashboards/supervisor-overview.tsx`
- Touch approvals chrome styles only if needed — **do not** change decide payload builders

**Interfaces:**
- Consumes: `listOpsCases({ status: "WAITING_APPROVAL" })` via existing client patterns, viz primitives
- Produces: waiting-count KPI + pipeline strip; links to `/supervisor/approvals`

- [ ] Implement + ensure `tests/browser/supervisor-approvals.test.tsx` still PASS unchanged in behavior.
- [ ] Check + commit `feat(web): supervisor overview viz`

---

### Task 7: Docs + final check

**Files:**
- Modify: `apps/web/README.md`, `apps/web/CHANGELOG.md`

- [ ] Document new `/` and `/login` flow, demo creds, screenshot commands.
- [ ] `make -C apps/web check` PASS.
- [ ] Commit `docs(web): Mercury shell routes and changelog`

---

## Execution notes

- After Task 3, Tasks 4–6 may run as parallel subagents in the same worktree if file ownership does not collide (different dashboard files).
- Task 2 must finish before 4–6 (shell dependency).
- Prefer `inherit` model for implementers on this host’s Free plan.
)
