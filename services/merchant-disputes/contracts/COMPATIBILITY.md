# merchant-disputes.v1 compatibility checklist

Contract baseline: `sentinel.task-contracts.v1`
SHA-256: `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`

## Produced

| Route | Request | Response |
| --- | --- | --- |
| `POST /v1/disputes` | Create body + optional `Idempotency-Key` | `DisputeCase`, 201 |
| `GET /v1/disputes/{dispute_id}` | Empty | `DisputeCase` |
| `POST /v1/disputes/{dispute_id}/packets` | Empty | `DisputeCase` |
| `POST /v1/disputes/{dispute_id}/submit` | Empty | `DisputeCase` |
| `POST /v1/disputes/{dispute_id}/resolve` | `{ outcome }` | `DisputeCase` |
| `GET /v1/disputes/{dispute_id}/deadline` | Empty | deadline view |

## Consumed (local stubs under `tests/stubs/`)

| Port | Stub cases |
| --- | --- |
| `case-api.v1` | valid, unavailable, malformed, unauthorized_or_out_of_scope |
| `evidence.v1` | valid, unavailable, malformed, unauthorized_or_out_of_scope |

## Real-peer adapter

HTTP adapters in `adapters/peers_http.py` reject unavailable (503), unauthorized (403), and malformed bodies (502). They never fall back to fixtures. `DISPUTES_MODE=real-peers` requires peer base URLs and tokens at boot.

## Assembly

Real-peer integration against SN-007/SN-006 remains **unverified** until owner assembly. Local checks use fixture peers only. No ledger writes.
