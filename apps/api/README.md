# SN-007 — Standalone authenticated case API (`case-api.v1`)

**Owned root:** `apps/api/`  
**Branch:** `feat/sn-007-case-api`  
**Package:** `sentinel-api`  
**Contract:** `sentinel.task-contracts.v1` · SHA-256 `0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa`

## What this module owns

Authenticated case intake/query/messages, immutable per-revision `CaseInput` snapshots, ordered durable events (JSON + SSE), operator queue/evidence proxy, supervisor decision proxy to the action ledger, escalation, internal workflow input/results, health/readiness/capabilities.

Authoritative approvals and money stay in the ledger. This API forwards the supervisor bearer token and exact `DecisionRequest` digest/revision; it does not mint approvals.

## Independence

Installs and checks with every other Sentinel task absent. Local doubles live under `tests/stubs/` for `workflow.v1`, `evidence.v1`, `action-ledger.v1`, and `verifier.v1` (valid / unavailable / malformed / unauthorized_or_out_of_scope). Disposable PostgreSQL via Docker proves restart and cursor-resumable events.

## Setup

```sh
cd apps/api
make setup          # uv sync --frozen
cp .env.example .env
```

Requires Docker for `make check` integration tests (private `postgres:17-alpine` container, tmpfs, removed after the session).

## Check

```sh
make -C apps/api check
```

Runs ruff lint/format check and pytest (unit, contract, integration).

## Preview

```sh
make -C apps/api preview
```

Uses `SENTINEL_API_*` from the environment (see `.env.example`). Fixture mode wires in-process peers; `real-peers` requires peer base URLs and rejects unavailable/malformed/unauthorized peers without fixture fallback.

## Auth

Opaque bearer tokens map to `Principal` via `fixtures/auth_tokens.json` (synthetic demo credentials only). Workflow/verifier principals deny empty `case_ids`; use explicit ids or `"*"`.

## Evidence labels

| Dimension | This module check |
| --- | --- |
| Component under test | Real `sentinel-api` implementation |
| Peers | Local fixture stubs under `tests/stubs/` |
| Database | Disposable local PostgreSQL |
| Payment provider / model | Not used |
| Assembly / pilot | Unverified |

Real-peer integration against independently built workflow/evidence/ledger/verifier services is an owner assembly concern.
