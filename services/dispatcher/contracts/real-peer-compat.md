# Real-peer compatibility checklist (dispatcher.v1)

Contract: `sentinel.task-contracts.v1` · SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`

| Check | Fixture status | Real-peer status |
| --- | --- | --- |
| Claim `POST /v1/actions/claims` with dispatcher principal | exercised via local stub | unverified |
| Submit `POST /v1/refunds` with `Idempotency-Key == provider_ref` | exercised via local stub | unverified |
| Lookup `GET /v1/refunds/{provider_ref}` | exercised via local stub | unverified |
| Report `POST /v1/actions/{action_id}/outcomes` PENDING / OUTCOME_UNKNOWN / ESCALATED | exercised via local stub | unverified |
| Timeout-after-commit reconciles original provider_ref only | PASS (fixture) | unverified |
| Crash/restart durable recovery | PASS (private PostgreSQL) | unverified |
| No reservation release on lease expiry alone | PASS (fixture) | unverified |
| Unavailable / malformed / unauthorized peers surface errors | PASS (stub modes) | unverified |

HTTP adapters: `sentinel_dispatcher.adapters.http_peers.HttpLedgerClient` and `HttpProviderClient`. They never fall back to fixtures when peers fail.

## Payment provider peer

Today the configured `payment-provider.v1` peer is the **mock sandbox simulator** (`services/simulator`). Evidence must stay labeled simulated/sandbox. A future real Paytm (or other) adapter must satisfy the same `payment-provider.v1` wire contract; dispatcher financial rules (stable `provider_ref` idempotency, no second ledger, no lease-expiry release) do not change for that swap.
