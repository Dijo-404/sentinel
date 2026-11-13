# SN-029 — merchant refund request workflow

Installable `merchant-refunds.v1` service. Merchant staff draft and submit refund
requests with evidence; policy and action-ledger ports own approval and reservation.
This module never mints provider refunds, never edits ledger tables, and never
treats `PENDING` as verified customer credit.

**Owned root:** `services/merchant-refunds/` · **Branch:** `feat/sn-029-merchant-refunds`

Contract: `sentinel.task-contracts.v1`, SHA-256
`0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.

## Standalone setup and checks

```sh
make -C services/merchant-refunds check
```

Uses only this module, local fixtures, and peer stubs under `tests/stubs/`.
No sibling Sentinel services, databases, or payment credentials required.

## Preview (fixture peers must be injected)

```sh
make -C services/merchant-refunds preview
```

Fixture mode refuses to start without injected peers (fail closed). Tests wire
stubs via `build_app(...)`. Real-peer mode needs non-demo bearer + peer base URLs
from `.env.example`.

## API sketch

| Method | Path | Notes |
| --- | --- | --- |
| `POST` | `/v1/refund-requests` | Draft create; requires `Idempotency-Key` |
| `PATCH` | `/v1/refund-requests/{id}` | Draft updates |
| `POST` | `/v1/refund-requests/{id}/submit` | Evidence + policy + ledger proposal |
| `POST` | `/v1/refund-requests/{id}/decisions` | Forward supervisor decision → reserve |
| `POST` | `/v1/refund-requests/{id}/sync` | Refresh from ledger; pending ≠ credit |
| `GET` | `/v1/capabilities` | Declares fixture \| real-peers mode |

Auth: `Authorization: Bearer token-merchant-refunds-demo` (synthetic local only).

## Consumed ports (local stubs)

| Port | Stub location | Modes |
| --- | --- | --- |
| `case-api.v1` | `tests/stubs/case_api.py` | valid / unavailable / malformed / unauthorized_or_out_of_scope |
| `policy.v1` | `tests/stubs/policy.py` | same |
| `action-ledger.v1` | `tests/stubs/ledger.py` | same; sole `action_id` mint |
| `evidence.v1` | `tests/stubs/evidence.py` | same |

Real-peer HTTP adapters: `src/sentinel_merchant_refunds/adapters/http_peers.py`.
Compatibility checklist: `contracts/real-peer-compat.md` (real assembly unverified).

## Financial boundary

SN-009 action-ledger remains the sole financial authority. This module only
proposes and tracks through injected ledger/policy ports. Integer minor units
only. `credit_verified` is true solely after ledger `CREDIT_CONFIRMED` maps to
`VERIFIED`.
