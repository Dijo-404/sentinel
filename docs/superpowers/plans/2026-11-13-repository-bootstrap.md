# Sentinel Repository Bootstrap Implementation Plan

> **For agentic workers:** Use native execution for this approved setup. Implement repository coordination only; the 26 application/component issues remain independent future work.

**Goal:** Install and publish a detailed, independently buildable agent-development baseline for Sentinel.

**Architecture:** Keep each module's code, tests, dependencies, migrations, configuration, documentation and changelog under its owned root. Root files govern repository policy and validate planning metadata; they do not impose a shared application build or wait for any service.

**Tech stack:** Python standard library for repository checks and GitHub task rendering/publication; GitHub CLI for authorized publication; GitHub Actions for repository checks. Python and TypeScript application implementations remain assigned tasks.

**Spec:** `docs/agent-workflow-design.md`, `docs/independent-task-contracts.md`, and `docs/tasks.json`, approved by the user's instruction to proceed on 13 November 2026.

## Global constraints

- Project name is Sentinel. Preserve existing source specifications and PDF bytes.
- All 26 tasks have zero completion prerequisites and disjoint primary roots.
- No root application manifest or shared lockfile; each module owns its setup.
- Models never grant financial authority. Keep the financial ledger's atomic state in one boundary.
- User approval covers local setup, initial empty-repository bootstrap, and publishing labels/issues. Later application PRs require owner review; agents never enable auto-merge or merge themselves.
- Work in the existing unborn checkout: no accepted commit exists from which to create an independent worktree. Initial main creation is the explicitly authorized setup exception.
- Do not implement or mark complete any of the 26 component tasks.

## Review focus

- A renamed/previously published task must not create a duplicate or reset claims/status.
- Missing peer implementations must not prevent another component's review/merge.
- Root checks must reject overlapping ownership, stale contract hashes and hidden optional MVP dependencies.
- Relative documentation links must remain inside the repo; local-only RTK includes need a portable fallback.
- Incomplete module scaffolds and fixture evidence must never imply product tests or release acceptance passed.

## Task 1: Detailed repository and module baseline

- [x] Create `AGENTS.md`, `CONTRIBUTING.md`, `README.md`, `CHANGELOG.md`, GitHub templates, CODEOWNERS, editor/git settings, environment example, and `Makefile`.
- [x] Create `docs/architecture.md`, `docs/repository-structure.md`, `docs/testing.md`, `docs/configuration.md`, and `docs/github-workflow.md`.
- [x] Populate each of the 26 task roots with its own detailed `README.md`, scoped `AGENTS.md`, and `CHANGELOG.md`. Do not add fake implementations or passing module checks.

## Task 2: Repository validation and publication tools

- [x] Write focused standard-library tests for task metadata validation, ownership conflicts, optional dependency mistakes, contract digests, idempotent issue lookup, and issue rendering.
- [x] Run tests before implementation and observe missing implementation failures.
- [x] Implement `scripts/repository/validate.py` and `scripts/repository/tasks.py` to meet those tests. Keep publication opt-in and preserve existing issues/labels.
- [x] Run root checks and tests; render all issue bodies and verify body size, task coverage, baseline hashes and local links.
- [x] Install a pinned-action GitHub workflow that runs repository checks without product services or provider secrets.

## Task 3: Review and publish the approved setup

- [x] Obtain one independent review of the whole setup. Correct important findings and rerun focused checks.
- [ ] Commit the explicitly reviewed initial file set and push the accepted bootstrap to `main` without force-pushing.
- [ ] Publish missing planning labels and the 26 independent, detailed task issues as ready and unassigned. Checkpoint the issue map and update the task register.
- [ ] Publish task issue references through a setup PR if further tracked changes are needed. Do not merge that PR automatically.
- [ ] Verify actual GitHub issue counts/statuses, main, and CI. Attempt supported/authorized main protection only after the required check exists; record platform limits accurately.

## Execution record

- Native execution selected to carry out the user's approved setup without another planning handoff.
- The initial checkout has no commits or application test commands. Baseline validation is the new repository suite; component tests stay explicitly unimplemented.

- Ruling: create initial issues in backlog against a reviewed local baseline commit, include the resulting issue map/register in the first main push, then activate ready together. This keeps ready tasks attached to an available main and avoids a later direct push to protected main.
- Repository tool tests: 19 passing; supplied specifications retain their intentional Markdown hard breaks.
- Independent review found two publication defects: a supplied commit could differ from rendered inputs, and recorded issue identities were not consulted after title/marker removal. Added committed-content verification, tracked/checkpoint identity reconciliation, and regression tests; the full suite passes.
