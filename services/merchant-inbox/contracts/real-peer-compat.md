# Real-peer compatibility checklist (merchant-inbox.v1)

Contract: `sentinel.task-contracts.v1` · SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`

| Check | Fixture status | Real-peer status |
| --- | --- | --- |
| List/filter synthetic PAID_UNFULFILLED, UNMATCHED_PAYMENT, PENDING_REFUND | PASS | unverified |
| Assign + notes transitions | PASS | unverified |
| Escalate → ESCALATED (not CLOSED / not resolved) | PASS | unverified |
| Merchant/tenant scope denial | PASS | unverified |
| case-api.v1 get + ops escalate | exercised via local stub | unverified |
| evidence.v1 case evidence read | exercised via local stub | unverified |
| Unavailable / malformed / unauthorized peers surface errors | PASS (stub modes) | unverified |

HTTP adapters: `sentinel_merchant_inbox.adapters.http_peers`. They never fall back to fixtures when peers fail.
