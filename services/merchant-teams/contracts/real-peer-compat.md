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

## Consumed peer: `identity.v1` (optional; enabled when `IDENTITY_BASE_URL` set)

When enabled in `real-peers`, identity is authoritative for membership grants:
local create / role / display-name updates are rejected; `POST /v1/staff/sync`
and `GET /v1/merchant/team` project and revoke against the peer response.

| Check | Expected |
| --- | --- |
| `GET /v1/merchant-memberships?tenant_id=&merchant_ref=` | 200 `{ contract_version, memberships[] }` |
| Membership row | `membership_id`, `assignment_id`, `user_id`, `tenant_id`, `merchant_ref`, `display_name`, `subroles[]`, `status` |
| Subroles | Merchant-scoped only: `viewer` \| `operator` \| `approver` \| `admin` |
| Unavailable / connection error | Surface `PEER_UNAVAILABLE` (503); no fixture fallback |
| 401 / 403 | Surface `PEER_UNAUTHORIZED` (403) |
| Non-JSON or schema mismatch | Surface `PEER_MALFORMED` (502) |
| Platform roles in `subroles` | Projection rejects; merchant-teams is not a second role authority |

## Produced wire types

- `MerchantStaff` — optional `approval_limit_minor` / `currency` omitted when unset
- `StaffActivity` — append-only timeline events (includes `MEMBERSHIP_PROJECTED` / `MEMBERSHIP_SYNCED` / `MEMBERSHIP_REVOKED`)

## Explicit non-goals

- No SN-009 ledger table writes
- No provider refund/dispatch calls
- Advisory limits never create `Approval` or reservations
- No competing platform role grants (`platform_admin`, `supervisor`, `risk_officer`, …)
- Real-peer mode never substitutes fixture success when case-api or configured identity fails

## Assembly status

Real-peer integration with a live case-api / identity build: **UNVERIFIED** until owner assembly.
Fixture/stub evidence only satisfies this component PR.
