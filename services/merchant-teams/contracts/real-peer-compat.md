# Real-peer compatibility checklist — merchant-teams.v1

Contract: `sentinel.task-contracts.v1`  
SHA-256: `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`

## Consumed peer: `case-api.v1`

| Check | Expected |
| --- | --- |
| `GET /v1/cases/{case_id}` with scoped bearer | 200 `Case` with `contract_version`, `case_id`, `revision`, `status` |
| Unavailable / connection error | Surface `PEER_UNAVAILABLE` (503); no fixture fallback |
| 401 / 403 | Surface `PEER_UNAUTHORIZED` (403) |
| Non-JSON or schema mismatch | Surface `PEER_MALFORMED` (502) |
| Unknown case | 404 `NOT_FOUND` |

## Produced wire types

- `MerchantStaff` — optional `approval_limit_minor` / `currency` omitted when unset
- `StaffActivity` — append-only timeline events

## Explicit non-goals

- No SN-009 ledger table writes
- No provider refund/dispatch calls
- Advisory limits never create `Approval` or reservations
- Real-peer mode never substitutes fixture success when case-api fails

## Assembly status

Real-peer integration with a live case-api build: **UNVERIFIED** until owner assembly.
Fixture/stub evidence only satisfies this component PR.
