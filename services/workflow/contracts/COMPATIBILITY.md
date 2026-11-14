# workflow.v1 compatibility checklist

Contract baseline: `sentinel.task-contracts.v1`
SHA-256: `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`

## Produced

| Route | Request | Response |
| --- | --- | --- |
| `POST /v1/runs` | `WorkflowRequest` | `Ack`, 202 |
| `POST /v1/workflow/risk-resume` | `RiskResumeRequest` | `Ack`, 202 |

`RiskResumeRequest`: `{ event_type, investigation_id, case_id, restriction_id, tenant_id, financial_approval_granted: false }`. Auth: `risk_officer`. Clearance never grants money; starts re-evaluation only.

## Consumed (local stubs under `tests/stubs/`)

| Port | Stub cases |
| --- | --- |
| `case-api.v1` | valid, unavailable, malformed, unauthorized_or_out_of_scope |
| `evidence.v1` | valid, unavailable, malformed, unauthorized_or_out_of_scope |
| `policy.v1` | valid, unavailable, malformed, unauthorized_or_out_of_scope |
| `action-ledger.v1` | valid, unavailable, malformed, unauthorized_or_out_of_scope |
| `verifier.v1` | valid, unavailable, malformed, unauthorized_or_out_of_scope |
| `risk.v1` blocks | valid, unavailable, malformed, unauthorized_or_out_of_scope |

## Real-peer adapter

HTTP adapters in `adapters/peers_http.py` and `adapters/model.py` (`HttpModelAdapter`) reject unavailable (503 peer), unauthorized (403), and malformed bodies. They never fall back to fixtures.

## Assembly

Real-peer integration against SN-006/007/005/009/011 remains **unverified** until owner assembly. Local checks use fixture peers and fake model only.
