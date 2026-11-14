# risk.v1 compatibility checklist

Contract baseline: `sentinel.task-contracts.v1`
SHA-256: `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`

## Produced

| Route | Request | Response |
| --- | --- | --- |
| `GET /v1/capabilities` | Empty | capabilities (`financial_authority=false`) |
| `GET /v1/risk/dashboard` | Empty | dashboard aggregates |
| `GET /v1/risk/investigations` | optional `case_id` | investigation list |
| `POST /v1/risk/investigations` | create body + optional `Idempotency-Key` | `Investigation`, 201 |
| `GET /v1/risk/investigations/{id}` | Empty | `Investigation` |
| `POST /v1/risk/investigations/{id}/findings` | finding body | `Finding`, 201 |
| `POST /v1/risk/restrictions/{id}/decision` | decision body | `RiskRestriction` |
| `GET /v1/risk/cases/{case_id}/blocks` | Empty | blocks flag |
| `POST /v1/ops/actions/{id}/decisions` | any | always `LEDGER_APPROVAL_FORBIDDEN` |
| `POST /v1/ledger/approvals` | any | always `LEDGER_APPROVAL_FORBIDDEN` |

## Consumed (local stubs under `tests/stubs/`)

| Port | Stub cases |
| --- | --- |
| `case-api.v1` | valid, unavailable, malformed, unauthorized_or_out_of_scope |
| `workflow` resume | valid, unavailable, malformed, unauthorized_or_out_of_scope |
| ledger approval | always denied locally (AUTH-21) |

## Real-peer adapter

HTTP adapters in `adapters/peers_http.py` reject unavailable (503), unauthorized (403), and malformed bodies (502). They never fall back to fixtures. `RISK_MODE=real-peers` requires peer base URLs/tokens and a durable store (`RISK_DATABASE_URL` or injected store).

## Assembly

Real-peer integration against case-api/workflow/policy remains **unverified** until owner assembly. Local checks use fixture peers only. No ledger writes. Restriction clearance resumes workflow evaluation only; supervisor approval remains separate (FLOW-11).
