# SN-007 — Standalone authenticated case API (`case-api.v1`)

**Owned root:** `apps/api/`  
**Branch:** `feat/sn-007-case-api`  
**Package:** `sentinel-api`  
**Contract:** `sentinel.task-contracts.v1` · SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`

## What this module owns

Authenticated case intake/query/messages, immutable per-revision `CaseInput` snapshots, ordered durable events (JSON + SSE), operator queue/evidence/claim, customer/operator/supervisor dashboard projections, supervisor decision proxy to the action ledger, escalation, internal workflow input/results, health/readiness/capabilities.

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

## Workflow outbox worker

Case mutations flush the workflow outbox opportunistically. For crash recovery and
continuous delivery (reclaim of stale `CLAIMED` leases), run a dedicated worker:

```sh
make -C apps/api flush-workflow
# or: uv run sentinel-api flush-workflow --loop --interval 2
# single pass: uv run sentinel-api flush-workflow --once
```

Lease window: 30s (`WORKFLOW_JOB_LEASE_SECONDS`). Expired or null leases on `CLAIMED`
rows are reclaimable.

## Order reference

Customer intake requires a subject-bound `order_reference`. Canonical form:
`{subject_ref}/{customer_order_id}` (example `subject-a/DEMO-ORDER-42`). That exact
string is stored on the case, CaseInput snapshots, and outbox scheduling payloads —
not stripped to a bare provider id when enqueueing workflow.

## Auth

`fixture` mode: composite principal resolution uses fixture identity session/BFF projections (`fixtures/identity_sessions.json`) for unknown bearers, with opaque service tokens from `fixtures/auth_tokens.json` taking precedence when present. `real-peers` mode: opaque TokenMap for workflow/dispatcher/verifier/`tok-*` service principals; when `IDENTITY_BASE_URL` (or `SENTINEL_API_IDENTITY_BASE_URL`) is set, unknown bearers are projected via identity `GET /v1/auth/me` (`active_assignment.role_id` → roles). Fail closed on identity unavailable/malformed responses; identity 401 falls through to TokenMap then denies. Non-loopback bind refuses identity session projection. Workflow/verifier principals deny empty `case_ids`; use explicit ids or `"*"`. Customer case create still requires `order_reference` bound to principal `subject_refs`.

## Evidence labels

| Dimension | This module check |
| --- | --- |
| Component under test | Real `sentinel-api` implementation |
| Peers | Local fixture stubs under `tests/stubs/` |
| Database | Disposable local PostgreSQL |
| Payment provider / model | Not used |
| Assembly / pilot | Unverified |

Real-peer integration against independently built workflow/evidence/ledger/verifier services is an owner assembly concern.
