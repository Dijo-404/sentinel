---
name: Independent agent task
about: One independently buildable component with supplied contracts and local peer doubles
title: "[SN-NEW] "
labels: agents, status:backlog
---

## Outcome

Describe one independently reviewable result. Register a stable SN task ID and disjoint root in docs/tasks.json through a PR.

## Ownership

- Task ID, lane, phase and priority:
- Owned root and any exact additional files:
- Feature branch:
- Human owner and agent/session (record upon claim):
- Task-completion prerequisites: **none**

## Supplied interfaces

- Baseline version, commit and content hash:
- Exact consumed/produced request-response types and errors:
- Optional ports that may stay disabled:
- Local peer doubles and valid/unavailable/malformed/unauthorized cases:

## Scope and clean architecture

- Observable behavior:
- Framework-free domain/use cases and injected ports:
- Adapters/composition and module-local state/migration ownership:
- Explicit non-goals:

## Deliverables and acceptance

- [ ] Local manifest/lockfile, configuration example and README.
- [ ] Typed boundary snapshots and deterministic fixtures/stubs.
- [ ] Meaningful behavior/failure tests and module-local `make check`.
- [ ] Checks pass without other task implementations or running services.
- [ ] Real-peer adapter fails clearly for missing/incompatible peers.
- [ ] Module changelog and exact evidence updated.

## Validation and assembly limits

- Exact local setup/run/check commands to implement:
- Required observed outcomes and negative cases:
- Real-component versus fixture/simulator/model evidence:
- Separate assembled verification, untested boundaries and next action:

Read AGENTS.md and CONTRIBUTING.md before claiming. Keep one status label. Owner review/merge is required; no agent auto-merge. An unfinished peer is not a blocker.
