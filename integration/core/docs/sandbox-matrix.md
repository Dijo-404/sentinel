# Canonical sandbox identity matrix

**Label:** sandbox / synthetic only. No production credentials, no live payments.

**Source of truth:** [../fixtures/sandbox-tokens.json](../fixtures/sandbox-tokens.json) (`tok-*` → principal; shared with #84).

Assembly extras (role→token lookup, base URLs, journey seeds, path label): [../fixtures/sandbox-assembly.json](../fixtures/sandbox-assembly.json).

Use this matrix so local `mode=real-peers` services share one tenant, case, port map, and opaque bearer strings.

## Shared identity

| Field | Value |
| --- | --- |
| `tenant_id` | `tenant-demo` |
| `case_id` | `case-demo-42` |
| `subject_ref` | `subject-demo-42` |
| `merchant_ref` | `merchant-demo-1` |
| `payment_provider` | `simulator` (never claim live) |

## Local ports (`127.0.0.1`)

| Peer | Port |
| --- | ---: |
| case API (`apps/api`) | 8080 |
| policy | 8005 |
| evidence | 8006 |
| workflow | 8088 |
| action-ledger | 8009 |
| dispatcher | 8010 |
| verifier | 8011 |
| identity (`services/identity`) | 8012 |
| risk (`services/risk`) | 8013 |
| merchant-disputes | 8030 |
| merchant-analytics | 8032 |
| payment simulator | 8094 |
| web shell | 3012 |

`identity` / `risk` are optional RBAC peers (not `REQUIRED_PEERS`). Fixture AUTH probes use path `rbac-fixture`.

## Shared opaque tokens

Same string is accepted by every peer that needs that role (plus cheap legacy aliases listed in the JSON).

| Token | Typical roles |
| --- | --- |
| `tok-workflow` | workflow service calls |
| `tok-dispatcher` | dispatcher → ledger / provider |
| `tok-verifier` | verifier service calls |
| `tok-case-api` | case API → workflow / peers |
| `tok-customer` | customer UI / case create |
| `tok-operator` | support operator (no ledger decide) |
| `tok-supervisor` | approval decisions |
| `tok-platform-admin` | staff invite / directory |
| `tok-risk-officer` | risk investigations (no money authority) |
| `tok-sandbox-admin` | simulator admin / demo-reset |

## Journey seed keys (simulator #82)

Order references match simulator journey packs. If #82 is not on `main` yet, simulator must expose these same keys.

| Journey | Seed key | Expectation |
| --- | --- | --- |
| pending | `JOURNEY-PENDING` | payment `PENDING` → `WAITING_ON_EVIDENCE` |
| merchant_mismatch | `JOURNEY-MISMATCH` | captured + unpaid order → `NEEDS_HUMAN` |
| duplicate_payment | `DEMO-ORDER-42` / `TXN-B` / `refund-demo-1` | 150000 minor, timeout recover, credit → `VERIFIED_RESOLVED` |
| refund_pending | `JOURNEY-REFUND-PENDING` / `refund-pending-1` | seeded provider `PENDING` ≠ customer credit |
| browser_to_credit | `subject-demo-42/DEMO-ORDER-42` + ledger digest seed | intake→SN-009→dispatcher→verifier→closure |
| duplicate_approval_deny | ledger operation `duplicate-approval-deny-demo` | conflicting decision denied; no refund |

Assembly drivers fail closed if a seed is missing.

## DB seed orchestrator

```sh
# From integration/core — refuses unless tenant-demo + SENTINEL_V1_SANDBOX=1
make seed-sandbox
# or: SENTINEL_V1_SANDBOX=1 uv run --frozen sentinel-core-assembly seed-sandbox
```

Wave peers (`merchant-analytics`, `merchant-disputes`, `risk`, `case-api`) run that
module’s `make seed` when the matching `*_DATABASE_URL` / `SENTINEL_API_DATABASE_URL`
env is set; otherwise `SKIPPED` with the manual `make -C <peer> seed` hint. Other
peers stay `SKIPPED` until hooked. Non-`tenant-demo` → `SANDBOX_TENANT_REQUIRED`.
Missing sandbox flag → `SANDBOX_FLAG_REQUIRED`. After seed + serve,
`make verify-wave0-1` / `./scripts/verify_wave0_1.sh` asserts HTTP 200 + seeded JSON
(fails without seed). Case-api seed leaves `case-seed-ops-escalated` (`ESCALATED`)
and `case-seed-ops-history` (`CLOSED_NO_ACTION`) for ops messages / audit / HISTORY.
After case-api serve + seed, `make verify-wave2` / `./scripts/verify_wave2.sh`
asserts those ops surfaces (case-api fixtures `token-operator` / `token-supervisor`);
optional `VERIFY_IDENTITY_TOKEN` hits identity `GET /v1/ops/team`.
Compose DB names: see [compose/init-databases.sql](../compose/init-databases.sql).

## Path honesty

- Default real-peers `HttpPeerBundle` path: `provider-sandbox-only` (payment-provider HTTP).
- With `SENTINEL_V1_AUTHORITY_PATH=1` and passing authority journeys: `path=browser-to-credit`,
  `sn009_authority_exercised=true` (still `assembled_mvp_claimed=false`).
- Fixture authority doubles: `path=browser-to-credit-fixture` when those journeys pass.
- Fixture RBAC probes path: `rbac-fixture` (AUTH-01 register deny, admin invite, AUTH-06 decide deny).
- `rbac-fixture` does **not** claim SN-009 authority or full money path.
- `SENTINEL_V1_REQUIRE_FULL_PATH=1` requires `path=browser-to-credit`; fails on provider-only.
- Peers advertise `mode=real-peers`; assembly still labels `payment_provider=simulator`.

## Evidence limits

- These tokens are disposable sandbox labels, not secrets of record.
- Passing module checks with this matrix is not assembled product or live-settlement evidence.
