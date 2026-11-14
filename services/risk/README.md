# SN-036 — Risk and fraud service

Standalone `risk.v1` service: fraud investigations, structured findings, and authorized financial-action restrictions. Restriction clearance never grants ledger approval.

**Owned root:** `services/risk/` · **Branch:** `feat/sn-036-risk` · **Issue:** #99

Contract: `sentinel.task-contracts.v1`, SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.

## Standalone setup and checks

```sh
make -C services/risk check
```

Installs only this module's `uv` dependencies (`pyproject.toml` / `uv.lock`). Uses in-process fixture peers for case-api and workflow resume. No sibling Sentinel services required. PostgreSQL via `RISK_DATABASE_URL` (required for `make seed` and real-peers durable state).

Preview (fixture mode, port **8013**):

```sh
cp services/risk/.env.example services/risk/.env
make -C services/risk preview
```

Sandbox seed (writes investigation + ACTIVE restriction + finding for `case-demo-42`):

```sh
# RISK_DATABASE_URL must point at Postgres
make -C services/risk seed
```

Stable seed ids: `inv-seed-case-demo-42`, `rst-seed-case-demo-42`, `fnd-seed-case-demo-42` (transaction_ref `TXN-B`). Evidence label: synthetic-sandbox. Idempotent upsert.

## Scope

- Owns investigations, findings and risk restrictions only.
- Creating an investigation opens an `ACTIVE` restriction with `blocks_financial_actions=true` (FLOW-10).
- Clearance emits a workflow resume event with `financial_approval_granted=false`; supervisor approval remains separate (FLOW-11).
- Risk principals calling ledger approval surfaces receive `LEDGER_APPROVAL_FORBIDDEN` (AUTH-21).
- Unauthorized tenant/case/queue scope and unavailable peers fail closed.
- Does **not** edit SN-009 ledger tables, mint refunds, or assign roles.

## Routes

| Method | Path | Auth | Notes |
| --- | --- | --- | --- |
| GET | `/healthz` | none | liveness |
| GET | `/readyz` | none | labels `mode` |
| GET | `/v1/capabilities` | none | `financial_authority=false` |
| GET | `/v1/risk/dashboard` | risk_officer | aggregates (portal analytics) |
| GET | `/v1/risk/reports` | risk_officer | dashboard + `report_kind=summary` (portal reports) |
| GET | `/v1/risk/investigations` | risk_officer | list (portal queue) |
| POST | `/v1/risk/investigations` | risk_officer | create + active restriction |
| GET | `/v1/risk/investigations/{id}` | risk_officer | get |
| POST | `/v1/risk/investigations/{id}/findings` | risk_officer | versioned finding |
| GET | `/v1/risk/findings` | risk_officer | list findings (portal audit); `?investigation_id=` / `?case_id=` |
| GET | `/v1/risk/restrictions` | risk_officer | list (portal holds/transactions); query `blocks_financial_actions`, `has_transaction_ref`, `status`, `case_id` |
| POST | `/v1/risk/restrictions/{id}/decision` | risk_officer | CLEAR/MAINTAIN/CONFIRM_FRAUD; requires `expected_revision` (CAS) |
| GET | `/v1/risk/cases/{case_id}/blocks` | risk_officer, workflow | blocks flag for portal + workflow hold gate |
| POST | `/v1/ops/actions/{id}/decisions` | any authed | always deny (AUTH-21) |
| POST | `/v1/ledger/approvals` | any authed | always deny (AUTH-21) |

### Portal page → route map

| Portal page | Peer GET |
| --- | --- |
| `/risk/queue` | `/v1/risk/investigations` |
| `/risk/holds` | `/v1/risk/restrictions?blocks_financial_actions=true` |
| `/risk/transactions` | `/v1/risk/restrictions?has_transaction_ref=true` |
| `/risk/analytics` | `/v1/risk/dashboard` |
| `/risk/reports` | `/v1/risk/reports` |
| `/risk/audit` | `/v1/risk/findings` |

## Local stubs

Under `tests/stubs/case_api/`, `tests/stubs/workflow/`, `tests/stubs/ledger/`: valid / unavailable / malformed / unauthorized, plus ledger deny double.

## Real-peer mode

Set `RISK_MODE=real-peers` plus `CASE_API_*`, `WORKFLOW_*`, and `RISK_DATABASE_URL` (or inject a durable store). Missing or failing peers surface as errors; fixture peers are never substituted. Assembly against live case-api/workflow is **unverified** until owner-run.

## Layout

```text
services/risk/
  src/sentinel_risk/
    domain/          # investigations, findings, restrictions
    application/     # RiskService + ports
    adapters/        # FastAPI, memory/postgres, peers
    bootstrap.py
  contracts/risk.v1.json
  tests/
```
