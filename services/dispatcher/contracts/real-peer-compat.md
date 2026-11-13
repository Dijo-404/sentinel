# Real-peer compatibility checklist (dispatcher.v1)

Contract: `sentinel.task-contracts.v1` · SHA-256 `0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa`

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
