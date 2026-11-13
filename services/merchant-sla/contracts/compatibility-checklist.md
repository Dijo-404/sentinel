# merchant-sla.v1 real-peer compatibility checklist

Contract baseline: `sentinel.task-contracts.v1` SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.

## Required peer: `case-api.v1`

| Check | Expected |
| --- | --- |
| `GET /v1/cases/{case_id}` authenticated | Case with `case_id`, `revision`, `status`, `language`, `intent`, `evidence_ids`, `contract_version` |
| `POST /v1/ops/cases/{case_id}/escalate` | Returns Case with `status=ESCALATED`; never `VERIFIED_RESOLVED` from escalation alone |
| Unavailable peer | Connect/timeout/5xx → surface `PEER_UNAVAILABLE` (503); no fixture fallback |
| Unauthorized / out of scope | 401/403 → `UNAUTHORIZED` / `FORBIDDEN`; fail closed |
| Malformed body | Non-JSON or missing required fields → `MALFORMED`; fail closed |

## Local modes

- `fixture`: in-process case stub under `tests/stubs/` / `adapters/case_api_fixture.py`. Labeled in `/v1/capabilities`.
- `real-peers`: HTTP adapter only. Missing base URL/token refuses boot. Never silently substitutes fixtures.

## Assembly status

Real-peer integration with a live SN-007 case API is **unverified** in this component PR. Fixture checks are not release evidence.
