# merchant-comms.v1 real-peer compatibility checklist

Pinned baseline: `sentinel.task-contracts.v1` SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.

## Required: case-api.v1

| Check | Expected |
| --- | --- |
| `GET /v1/cases/{case_id}` with scoped bearer | `Case` JSON matching snapshot |
| Unavailable / 5xx / network error | `PEER_UNAVAILABLE` (503); no fixture fallback |
| Malformed body | `MALFORMED_RESPONSE` (502); no fixture fallback |
| Unauthorized / out-of-scope | `NOT_FOUND` (404); fail closed |

## Optional: indic-context.v1

| Check | Expected |
| --- | --- |
| `POST /v1/proposals` available | Status body derived from `ModelResult`; not financial authority |
| Unavailable / malformed / unauthorized | Deterministic EN/TA/HI template with `[fake]` label |
| Not configured | Same labeled fake template path |

## Assembly evidence status

- Fixture / local stubs: exerciseable via `make check`
- Real case-api peer: **unverified** until owner assembly
- Real indic-context peer: **unverified** (optional)
- Payment simulator / live model / pilot: **not applicable** (no financial writes)
