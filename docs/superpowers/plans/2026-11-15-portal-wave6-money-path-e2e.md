# Portal Wave 6: Money-path E2E + program honesty gate

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove sandbox money path (intake → SN-009 → dispatcher → simulator → verifier) under assembly with honesty labels; gate that portal stubs are gone; real approval-ui on real-peers path; no silent fixture fallback. Close the portal DB-backed program (owner review still required for MVP claim).

**Architecture:** Extend `integration/core` with `verify-wave6` that (1) asserts portal stub inventory empty in `apps/web`, (2) runs fixture assembly journeys including authority journeys when selected, (3) checks report honesty fields (`payment_provider=simulator`, path labels, `sn009_authority_exercised` when authority path on), (4) smoke-imports SN-013 `ApprovalPanel` and asserts web real-peers approval slot does not embed local substitute. Live `real-peers` stack remains runbook-driven (`run_sandbox_journeys.sh`); module `make check` stays credential-free.

**Tech Stack:** integration/core (uv/pytest), apps/web (Vitest assertions), packages/approval-ui.

**Spec:** `docs/superpowers/specs/2026-11-15-portal-db-backed-completion-design.md` (Wave 6 + program acceptance)

## Global Constraints

- Contract SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`
- Simulator only — never live payment credentials
- SN-009 sole money authority; assistants/voice never decide
- Assembled MVP claim remains **owner review** after this wave — do not auto-claim release
- Worktree: `/home/dj/projects/sentinel-portal-wave0-1` · `feat/portal-wave6-money-path-e2e`

## Review Focus

- Fixture journey suite PASS in `make -C integration/core check`
- verify-wave6 fails if any `apps/web` product page still has “Not available yet” / “Fixture placeholder” / “not connected to its service yet”
- Report labels never claim live provider
- Real-peers approval path uses package panel (prior wave) — re-assert in gate

---

### Task 1: Portal stub inventory scanner

**Files:**

- Create: `integration/core/src/sentinel_core_assembly/adapters/portal_stub_scan.py`
- Create: `integration/core/tests/test_portal_stub_scan.py`
- Optional: Makefile target used by verify-wave6

**Interfaces:**

- `scan_portal_stubs(web_app_root: Path) -> StubScanReport` with `status: PASS|FAIL`, `hits: list[{path, line, text}]`
- Patterns: `Not available yet`, `Fixture placeholder`, `not connected to its service yet`
- Scan `apps/web/src/app/**/*.{tsx,ts}` relative to repo root discovered from integration/core

- [ ] **Steps: TDD (fail if planted fixture string in tmp; pass on current tree), commit** `feat(integration): portal stub inventory scanner`

---

### Task 2: Assembly honesty assertions in fixture journeys

**Files:**

- Modify journey/report tests under `integration/core/tests/`
- Modify domain/report builders only if a label is wrong
- README honesty section

**Interfaces:**

- Fixture `sentinel-core-assembly run --mode fixture` report must include:
  - `payment_provider == "simulator"` (or documented equivalent field)
  - `path` in `{fixture, authority-fixture, …}` — never `live-provider`
  - When authority journeys included: `sn009_authority_exercised is true` for browser_to_credit check
- Fail closed if evidence_mode fixture sneaks into a real-peers probe helper (existing negatives OK — extend if gap)

- [ ] **Steps: TDD, `make -C integration/core check`, commit** `test(integration): money-path honesty labels`

---

### Task 3: Web real-peers approval + composition gate tests

**Files:** `apps/web/tests/` — composition default real-peers; approval-slot real-peers ≠ local substitute; voice enabled path fail-closed already exists — add/confirm

**Interfaces:**

- Test: `loadShellConfig({})` mode is `real-peers`
- Test: ApprovalSlot with mode real-peers does not set `data-slot="approval-ui.v1-local"`
- Commit under apps/web if new tests needed

- [ ] **Steps: check, commit** `test(web): real-peers approval and mode gates`

---

### Task 4: `verify-wave6` aggregator + Makefile/script

**Files:**

- `integration/core/src/sentinel_core_assembly/adapters/verify_wave6.py`
- `integration/core/scripts/verify_wave6.sh`
- Makefile `verify-wave6`, CLI entry, README, CHANGELOG
- Tests: scanner fail injected; honesty fields on fixture assembly invoke; approval import smoke

**Interfaces:**

- `verify_wave6(env) -> VerifyReport` checks:
  1. portal stub scan PASS
  2. fixture assembly journeys PASS (in-process)
  3. `ApprovalPanel` importable from approval-ui package path
  4. optional: if `VERIFY_WAVE6_LIVE=1` and peers up, run subset of real-peers journeys — else skip live with documented skip
- Program index Wave 6 → done; note program complete pending owner MVP review

- [ ] **Steps: TDD, check, commit** `feat(integration): wave 6 money-path verify`

---

### Task 5: Program completion docs

**Files:**

- Update `docs/superpowers/plans/2026-11-15-portal-db-backed-program.md` — all waves done; owner gate for MVP
- Spec status note or short `docs/superpowers/plans/2026-11-15-portal-program-complete.md` pointer (optional thin)
- sandbox-runbook: wave6 verify command

- [ ] **Steps: commit** `docs: portal DB-backed program wave 6 complete`

---

## Execution notes

- Do not start live payment rails.
- Do not merge claim of product release into README beyond “sandbox journeys + owner review”.
- After Task 5: push/PR/merge per user habit, then stop (program waves complete).
