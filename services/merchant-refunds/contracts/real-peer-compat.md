# Real-peer compatibility checklist (merchant-refunds.v1)

Contract: `sentinel.task-contracts.v1` · SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`

| Check | Fixture status | Real-peer status |
| --- | --- | --- |
| Draft → submit → `AWAITING_APPROVAL` via policy + ledger proposal | PASS | unverified |
| Supervisor decision → ledger reserve → `RESERVED` | PASS | unverified |
| Policy DENY / peer failure leaves no forged `action_id` | PASS | unverified |
| Sync: `PENDING`/`PROVIDER_CONFIRMED` ≠ `credit_verified` | PASS | unverified |
| Sync: `CREDIT_CONFIRMED` → `VERIFIED` | PASS | unverified |
| case-api / evidence / policy / ledger unavailable|malformed|unauthorized | PASS (stub + HTTP adapters) | unverified |
| No payment-provider write adapter | PASS (source scan) | n/a |

HTTP adapters: `sentinel_merchant_refunds.adapters.http_peers`. They never fall back to fixtures when peers fail.
