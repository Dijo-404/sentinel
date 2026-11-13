# Real-peer compatibility checklist (verifier.v1)

Contract: `sentinel.task-contracts.v1` · SHA-256 `0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa`

| Check | Fixture status | Real-peer status |
| --- | --- | --- |
| `POST /v1/webhooks/simulator` original-byte HMAC + tenant map + replay | PASS | unverified |
| Durable inbox dedupe / out-of-order reconcile | PASS (private PostgreSQL) | unverified |
| `POST /v1/rechecks` with Idempotency-Key | PASS | unverified |
| `POST /v1/assessments` + `GET /v1/assessments/{id}` | PASS | unverified |
| Provider `GET /v1/refunds/{provider_ref}` + `GET /v1/credits/{provider_ref}` | exercised via local stub | unverified |
| Ledger `GET /v1/actions/{id}` + `POST .../outcomes` evidence transitions | exercised via local stub | unverified |
| Evidence + case-api result announcement after credit | exercised via local stub | unverified |
| Pending ≠ provider-confirmed ≠ credit-confirmed | PASS | unverified |
| Unavailable / malformed / unauthorized peers surface errors | PASS (stub modes) | unverified |

HTTP adapters: `sentinel_verifier.adapters.http_peers`. They never fall back to fixtures when peers fail.
