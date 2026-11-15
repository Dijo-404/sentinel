# SN-028 — merchant exception inbox

**State:** implemented. Local `make check` exercises `merchant-inbox.v1` with synthetic exception fixtures and local case-api/evidence stubs only.

**Owned root:** `services/merchant-inbox/`
**Branch:** `feat/sn-028-merchant-inbox`
**Produces:** `merchant-inbox.v1`
**Consumes (stubs):** `case-api.v1`, `evidence.v1`

Contract baseline: `sentinel.task-contracts.v1` · SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.

## Outcome

Merchant-scoped inbox for `PAID_UNFULFILLED`, `UNMATCHED_PAYMENT`, and `PENDING_REFUND` items. Staff can filter, assign, note, and escalate. Escalation sets `ESCALATED` and never `CLOSED`; it is not verified financial resolution. Integer `amount_minor` only. No ledger write authority.

## Setup and check

Requires `uv` on PATH. No sibling Sentinel service, shared lockfile, or PostgreSQL.

```sh
make -C services/merchant-inbox check
```

Observed mode: `fixture`. Peer doubles live under `tests/stubs/` (and `adapters/local_peers.py` for preview).

## Run locally

```sh
cp services/merchant-inbox/.env.example services/merchant-inbox/.env   # optional
make -C services/merchant-inbox preview
# listens on MERCHANT_INBOX_HOST/PORT (default 127.0.0.1:8028)
```

Synthetic tokens are in `contracts/principals.json`. Example merchant operator bearer: `merchant-op-demo-token` scoped to `merchant-demo-1`.

## Routes

| Method | Path                                         | Auth                         | Notes                                                           |
| ------ | -------------------------------------------- | ---------------------------- | --------------------------------------------------------------- |
| GET    | `/healthz`                                   | none                         | liveness                                                        |
| GET    | `/readyz`                                    | none                         | labels `mode`                                                   |
| GET    | `/v1/capabilities`                           | none                         | `contract_version`, `component=merchant-inbox`, `mode`          |
| GET    | `/v1/exceptions?merchant_ref=&kind=&status=` | merchant operator/supervisor | list/filter                                                     |
| GET    | `/v1/exceptions/{item_id}`                   | merchant operator/supervisor | enriches case-linked items via peers                            |
| POST   | `/v1/exceptions/{item_id}/assign`            | merchant operator/supervisor | `{ assignee }` → `ASSIGNED`                                     |
| POST   | `/v1/exceptions/{item_id}/notes`             | merchant operator/supervisor | `{ note }`                                                      |
| POST   | `/v1/exceptions/{item_id}/escalate`          | merchant operator/supervisor | `{ reason_code, owner_queue? }` → `ESCALATED`, `resolved=false` |

## Layout

```text
services/merchant-inbox/
  src/sentinel_merchant_inbox/
    domain/          # assign/note/escalate invariants
    application/     # MerchantInboxService + ports
    adapters/        # FastAPI, token map, memory store, HTTP peers, local peers
    bootstrap.py
  contracts/         # principals, fixture items, port snapshot, real-peer checklist
  tests/             # acceptance + fail-closed peer modes
  tests/stubs/       # case-api.v1 + evidence.v1 doubles
```

## Evidence limits

- Standalone fixture check only. Real-peer assembly with live case-api/evidence is unverified here (`contracts/real-peer-compat.md`).
- No production credentials, real-money movement, or live payment peers.
- Financial reservation/dispatch remains SN-009/SN-010 authority; this service owns inbox workflow state only.
