# SN-008 — Independent durable workflow worker

**Package:** `sentinel-workflow` · **Port:** `workflow.v1`  
**Contract:** `sentinel.task-contracts.v1` · SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`

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
- `POST /v1/workflow/risk-resume` → `Ack` 202 (`RiskResumeRequest`, `risk_officer` only); re-evaluates case without money approval
- Auth: synthetic bearer tokens from `WORKFLOW_AUTH_TOKENS` (empty `case_ids` deny; `"*"` allows all)
- DECISION resume reads supervisor approval from `ledger.get_action(...).approval` only (no HTTP forge header)
- Financial path consults risk hold lookup (`WORKFLOW_PEER_RISK_URL` in real-peers); active hold or peer failure escalates fail-closed
- `GET /v1/capabilities` reports `mode: fixture|real-peers`
- Fake model scenarios via `WORKFLOW_FAKE_MODEL_SCENARIO` (`proposal`, `needs_input`, `escalate`, `malformed`, `outage`)
- Peer error escalations carry the peer's code: a coded `PeerError` from ledger/policy/verifier/risk escalates with `reason_code` `<PEER>_<CODE>` (e.g. `LEDGER_APPROVAL_EXPIRED`, `LEDGER_POLICY_DENIED`); unavailable peers or codes outside `[A-Z][A-Z0-9_]{1,63}` keep the old `LEDGER_PEER_FAILURE` / `POLICY_PEER_FAILURE` / `VERIFIER_PEER_FAILURE` / `RISK_PEER_UNAVAILABLE` / `RISK_PEER_FAILURE`. `ORDER_REFERENCE_REQUIRED` stays unprefixed. Each is logged at warning level with code and message
- `job_key` redelivery: same payload re-executes only a `failed` job (atomic `failed`→`running` claim, so concurrent redeliveries run once); `accepted`/`running`/`completed` jobs return 202 without re-running; a different payload is `IDEMPOTENCY_CONFLICT`

## Layout

| Path                                 | Role                                                               |
| ------------------------------------ | ------------------------------------------------------------------ |
| `src/sentinel_workflow/domain/`      | Wire types, canonical action digest                                |
| `src/sentinel_workflow/application/` | Accept/run/outbox use cases and ports                              |
| `src/sentinel_workflow/graph/`       | LangGraph nodes and compile                                        |
| `src/sentinel_workflow/adapters/`    | HTTP API, Postgres, fake/HTTP model, real-peer HTTP, fixture peers |
| `contracts/`                         | Request/ack/digest snapshots + compatibility checklist             |
| `tests/stubs/`                       | Local doubles for evidence/policy/ledger/verifier/case-api         |
| `migrations/`                        | Module-owned schema reference                                      |

## Acceptance coverage

- Approval interrupt survives Postgres restart; authenticated DECISION resume; ledger `operation_key` prevents duplicate logical financial commands on node replay
- Missing evidence → `NEEDS_INPUT`; malformed/outage model → `ESCALATED`; exhausted investigation budget → `ESCALATED`; pending verification → `WAITING_EXTERNAL`
- Outbox retries on case-api outage; idempotent `job_key`; failed job retried once on redelivery; unauthorized token rejected
- Ledger 409 codes reach the case result and warning log
- Real HTTP peer adapters raise on unavailable/unauthorized/malformed (no fixture fallback)

## Evidence labels

| Dimension             | This module's local check        |
| --------------------- | -------------------------------- |
| Component under test  | Real `sentinel-workflow`         |
| Payment provider      | Not called (ledger stub only)    |
| Model                 | Fake (labeled)                   |
| Peers                 | Local stubs under `tests/stubs/` |
| Assembly / real peers | Unverified                       |

## Ownership

Work only in `services/workflow/**`. See [AGENTS.md](AGENTS.md).
