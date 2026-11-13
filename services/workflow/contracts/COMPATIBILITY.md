# workflow.v1 compatibility checklist

Contract baseline: `sentinel.task-contracts.v1`
SHA-256: `0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa`

## Produced

| Route | Request | Response |
| --- | --- | --- |
| `POST /v1/runs` | `WorkflowRequest` | `Ack`, 202 |

## Consumed (local stubs under `tests/stubs/`)

| Port | Stub cases |
| --- | --- |
| `case-api.v1` | valid, unavailable, malformed, unauthorized_or_out_of_scope |
| `evidence.v1` | valid, unavailable, malformed, unauthorized_or_out_of_scope |
| `policy.v1` | valid, unavailable, malformed, unauthorized_or_out_of_scope |
| `action-ledger.v1` | valid, unavailable, malformed, unauthorized_or_out_of_scope |
| `verifier.v1` | valid, unavailable, malformed, unauthorized_or_out_of_scope |

## Real-peer adapter

HTTP adapters in `adapters/peers_http.py` and `adapters/model.py` (`HttpModelAdapter`) reject unavailable (503 peer), unauthorized (403), and malformed bodies. They never fall back to fixtures.

## Assembly

Real-peer integration against SN-006/007/005/009/011 remains **unverified** until owner assembly. Local checks use fixture peers and fake model only.
