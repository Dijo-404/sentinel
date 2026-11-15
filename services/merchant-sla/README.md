# SN-031 — merchant SLA and task management

**State:** implemented. Local `make check` exercises `merchant-sla.v1` with fixture principals and a local `case-api.v1` stub only.

**Owned root:** `services/merchant-sla/`
**Branch:** `feat/sn-031-merchant-sla`
**Produces:** `merchant-sla.v1`
**Consumes:** `case-api.v1` (local stubs; real-peer HTTP adapter fail-closed)

Contract baseline: `sentinel.task-contracts.v1` · SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.

## Outcome

Configure merchant respond/resolve targets (`SlaPolicy`), assign case tasks (`SlaTask`), highlight overdue work against an injectable/virtual clock, and schedule follow-ups. Escalating a task sets status `ESCALATED` and asks case-api to escalate the case — it does **not** mark the task `DONE` and never treats the case as financially resolved (`VERIFIED_RESOLVED`).

## Setup and check

Requires `uv` on PATH. No sibling Sentinel service, shared lockfile, or PostgreSQL.

```sh
make -C services/merchant-sla check
```

This syncs the module lockfile, runs ruff, then pytest (unit + HTTP contract + fail-closed peers). Observed mode: `fixture`.

## Run locally

```sh
cp services/merchant-sla/.env.example services/merchant-sla/.env   # optional documentation only
make -C services/merchant-sla preview
# listens on MERCHANT_SLA_HOST/MERCHANT_SLA_PORT (default 127.0.0.1:8031)
```

Synthetic tokens are in `contracts/principals.json`. Example bearer: `merchant-ops-demo-token`.

## Routes

| Method | Path                             | Auth                | Notes                                                |
| ------ | -------------------------------- | ------------------- | ---------------------------------------------------- |
| GET    | `/healthz`                       | none                | liveness                                             |
| GET    | `/readyz`                        | none                | labels `mode`                                        |
| GET    | `/v1/capabilities`               | none                | `contract_version`, `component=merchant-sla`, `mode` |
| POST   | `/v1/policies`                   | merchant ops bearer | upsert `SlaPolicy`                                   |
| GET    | `/v1/policies/{policy_id}`       | merchant ops bearer | fetch policy                                         |
| GET    | `/v1/policies?merchant_ref=`     | merchant ops bearer | list policies                                        |
| POST   | `/v1/tasks`                      | merchant ops bearer | create task from case + policy                       |
| GET    | `/v1/tasks/{task_id}`            | merchant ops bearer | fetch task (refreshes `overdue`)                     |
| GET    | `/v1/tasks`                      | merchant ops bearer | filter by merchant/case/`overdue_only`               |
| POST   | `/v1/tasks/{task_id}/assign`     | merchant ops bearer | set assignee                                         |
| POST   | `/v1/tasks/{task_id}/follow-ups` | merchant ops bearer | schedule `follow_up_at`                              |
| POST   | `/v1/tasks/{task_id}/escalate`   | merchant ops bearer | `ESCALATED` ≠ `DONE` / financial resolve             |
| POST   | `/v1/tasks/{task_id}/complete`   | merchant ops bearer | explicit non-financial `DONE`                        |

## Local peers

`tests/stubs/` covers `case-api.v1` cases: `valid`, `unavailable`, `malformed`, `unauthorized_or_out_of_scope`. Real-peer mode (`MERCHANT_SLA_MODE=real-peers`) requires `MERCHANT_SLA_CASE_API_BASE_URL` and `MERCHANT_SLA_CASE_API_TOKEN` and never falls back to fixtures.

## Layout

```text
services/merchant-sla/
  src/sentinel_merchant_sla/
    domain/          # due dates, overdue, escalate≠done
    application/     # MerchantSlaService + ports
    adapters/        # FastAPI, bearer map, clocks, memory store, case peers
    bootstrap.py
  contracts/         # principals, wire examples, compatibility checklist
  tests/stubs|unit|contract
```

## Evidence limits

- Standalone fixture check only. Real-peer assembly with live SN-007 case API is unverified here.
- No production credentials, real-money movement, or ledger writes. Financial authority remains SN-009 / SN-010.
- Fixture peers cannot satisfy product release evidence.
