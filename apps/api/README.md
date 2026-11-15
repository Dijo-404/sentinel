# SN-007 — Standalone authenticated case API (`case-api.v1`)

**Owned root:** `apps/api/`  
**Branch:** `feat/sn-007-case-api`  
**Package:** `sentinel-api`  
**Contract:** `sentinel.task-contracts.v1` · SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`

## What this module owns

Authenticated case intake/query/messages, immutable per-revision `CaseInput` snapshots, ordered durable events (JSON + SSE), operator queue/evidence/claim, ops message inbox + audit event feed, customer/operator/supervisor dashboard projections, supervisor decision proxy to the action ledger, escalation, internal workflow input/results, health/readiness/capabilities.

### Ops list projections

Operator and supervisor only (customer → 403). All tenant-scoped; empty list is honest empty, never fixture rows.

| Endpoint                     | Notes                                                                                                                                                                                                                                                 |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GET /v1/ops/cases?status=…` | Queue filter. Exact `CaseState`, comma-separated states, or alias `HISTORY` = `{VERIFIED_RESOLVED, CLOSED_NO_ACTION}`. Max 50; optional `after` cursor.                                                                                               |
| `GET /v1/ops/messages`       | Newest-first inbox from `case_messages`. Shape `{ messages: [{ case_id, message_id, text, language, author, occurred_at }], next_cursor? }`. Max 50.                                                                                                  |
| `GET /v1/ops/audit-events`   | Newest-first case events. Shape `{ events: [{ case_id, sequence, type, occurred_at, payload }], next_cursor? }`. Max 50. Returns stored `payload_json` as-is; writers already persist only sanitized domain fields (no separate read-path redaction). |

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

## Sandbox seed

```sh
# Requires SENTINEL_V1_SANDBOX=1 (or SENTINEL_API_SANDBOX=1) + SENTINEL_API_DATABASE_URL
# Tenant must be tenant-demo (CORE_ASSEMBLY_TENANT_ID / SENTINEL_API_TENANT_ID).
make -C apps/api seed
```

Inserts synthetic ops rows for portal wave 2 surfaces:

| Seed case                 | Status             | Surfaces                                        |
| ------------------------- | ------------------ | ----------------------------------------------- |
| `case-seed-ops-escalated` | `ESCALATED`        | escalations queue, messages inbox, audit events |
| `case-seed-ops-history`   | `CLOSED_NO_ACTION` | HISTORY filter, messages, audit events          |

Non-`tenant-demo` → `SANDBOX_TENANT_REQUIRED`. Missing sandbox flag → `SANDBOX_FLAG_REQUIRED`. Non-Postgres URL → `POSTGRES_URL_REQUIRED`. Idempotent re-seed. Orchestrated via `make -C integration/core seed-sandbox` when `SENTINEL_API_DATABASE_URL` is set.

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

Delivery outcome classification:

| Workflow response                        | Outbox result                                                   |
| ---------------------------------------- | --------------------------------------------------------------- |
| 2xx `accepted: true`                     | `DELIVERED`                                                     |
| 5xx / network error (`PEER_UNAVAILABLE`) | `PENDING`, redelivered on the next pass (unbounded)             |
| 409 / 422 / 429 (`PEER_REJECTED_<code>`) | `PENDING` with exponential backoff; `FAILED` after max attempts |
| 400 / 401 / 403 / 404 / malformed body   | `FAILED` immediately                                            |

Transient retry settings: `SENTINEL_API_WORKFLOW_RETRY_MAX_ATTEMPTS` (default 5),
`SENTINEL_API_WORKFLOW_RETRY_BASE_SECONDS` (default 2; delay doubles per attempt),
`SENTINEL_API_WORKFLOW_RETRY_MAX_SECONDS` (default 300 cap). `attempts` counts
transient rejections; a deferred `PENDING` row stores its next attempt time in
`lease_expires_at`. Existing databases need migration `0004`
(`uv run alembic upgrade head`): `create_all` does not add columns to an existing table.

## Order reference

Customer intake requires a subject-bound `order_reference`. Canonical form:
`{subject_ref}/{customer_order_id}` (example `subject-a/DEMO-ORDER-42`). That exact
string is stored on the case, CaseInput snapshots, and outbox scheduling payloads —
not stripped to a bare provider id when enqueueing workflow.

## Auth

`fixture` mode: composite principal resolution uses fixture identity session/BFF projections (`fixtures/identity_sessions.json`) for unknown bearers, with opaque service tokens from `fixtures/auth_tokens.json` taking precedence when present. `real-peers` mode: opaque TokenMap for workflow/dispatcher/verifier/`tok-*` service principals; when `IDENTITY_BASE_URL` (or `SENTINEL_API_IDENTITY_BASE_URL`) is set, unknown bearers are projected via identity `GET /v1/auth/me` (`active_assignment.role_id` → roles). Fail closed on identity unavailable/malformed responses; identity 401 falls through to TokenMap then denies. Non-loopback bind refuses identity session projection. Workflow/verifier principals deny empty `case_ids`; use explicit ids or `"*"`. Customer case create still requires `order_reference` bound to principal `subject_refs`.

## Evidence labels

| Dimension                | This module check                        |
| ------------------------ | ---------------------------------------- |
| Component under test     | Real `sentinel-api` implementation       |
| Peers                    | Local fixture stubs under `tests/stubs/` |
| Database                 | Disposable local PostgreSQL              |
| Payment provider / model | Not used                                 |
| Assembly / pilot         | Unverified                               |

Real-peer integration against independently built workflow/evidence/ledger/verifier services is an owner assembly concern.
