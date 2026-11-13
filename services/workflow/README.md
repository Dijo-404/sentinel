# SN-008 — Independent durable workflow worker

**Package:** `sentinel-workflow` · **Port:** `workflow.v1`  
**Contract:** `sentinel.task-contracts.v1` · SHA-256 `0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa`

## Outcome

Bounded typed LangGraph worker: investigation → planning → policy → approval interrupt → ledger propose/reserve → verification/wait. Module-owned PostgreSQL checkpointer, jobs, decisions, and case-result outbox. Baseline **fake** structured model (clearly labeled) plus configurable HTTP model adapter. Phase 2 `indic-context` is not required.

## Setup

Requires Python 3.11+, [uv](https://github.com/astral-sh/uv), and Docker (disposable Postgres for `make check`).

```sh
cd services/workflow
cp .env.example .env   # optional local overrides
uv sync --frozen
make check
```

`make check` runs ruff + pytest. Integration tests start a private `postgres:17-alpine` container (tmpfs, removed after the session). No sibling Sentinel services are required.

## Run (local fixture peers + fake model)

```sh
# Postgres URL in WORKFLOW_DATABASE_URL, then:
uv run sentinel-workflow migrate
uv run sentinel-workflow serve
```

- `POST /v1/runs` → `Ack` 202 (`WorkflowRequest`)
- Auth: synthetic bearer tokens from `WORKFLOW_AUTH_TOKENS`
- DECISION resume may include `X-Sentinel-Approval` JSON for authenticated approval payload in fixture/assembly tests
- `GET /v1/capabilities` reports `mode: fixture|real-peers`
- Fake model scenarios via `WORKFLOW_FAKE_MODEL_SCENARIO` (`proposal`, `needs_input`, `escalate`, `malformed`, `outage`)

## Layout

| Path | Role |
| --- | --- |
| `src/sentinel_workflow/domain/` | Wire types, canonical action digest |
| `src/sentinel_workflow/application/` | Accept/run/outbox use cases and ports |
| `src/sentinel_workflow/graph/` | LangGraph nodes and compile |
| `src/sentinel_workflow/adapters/` | HTTP API, Postgres, fake/HTTP model, real-peer HTTP, fixture peers |
| `contracts/` | Request/ack/digest snapshots + compatibility checklist |
| `tests/stubs/` | Local doubles for evidence/policy/ledger/verifier/case-api |
| `migrations/` | Module-owned schema reference |

## Acceptance coverage

- Approval interrupt survives Postgres restart; authenticated DECISION resume; ledger `operation_key` prevents duplicate logical financial commands on node replay
- Missing evidence → `NEEDS_INPUT`; malformed/outage model → `ESCALATED`; exhausted investigation budget → `ESCALATED`; pending verification → `WAITING_EXTERNAL`
- Outbox retries on case-api outage; idempotent `job_key`; unauthorized token rejected
- Real HTTP peer adapters raise on unavailable/unauthorized/malformed (no fixture fallback)

## Evidence labels

| Dimension | This module's local check |
| --- | --- |
| Component under test | Real `sentinel-workflow` |
| Payment provider | Not called (ledger stub only) |
| Model | Fake (labeled) |
| Peers | Local stubs under `tests/stubs/` |
| Assembly / real peers | Unverified |

## Ownership

Work only in `services/workflow/**`. See [AGENTS.md](AGENTS.md).
