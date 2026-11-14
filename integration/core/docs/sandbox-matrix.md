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

Assembly drivers fail closed if a seed is missing.

## Path honesty

- Current `HttpPeerBundle` path: `provider-sandbox-only` (payment-provider HTTP).
- Fixture RBAC probes path: `rbac-fixture` (AUTH-01 register deny, admin invite, AUTH-06 decide deny).
- Reports set `assembled_mvp_claimed=false`, `sn009_authority_exercised=false`.
- `rbac-fixture` does **not** claim SN-009 authority or full money path.
- `SENTINEL_V1_REQUIRE_FULL_PATH=1` fails closed while path remains provider-only.
- Peers advertise `mode=real-peers`; assembly still labels `payment_provider=simulator`.

## Evidence limits

- These tokens are disposable sandbox labels, not secrets of record.
- Passing module checks with this matrix is not assembled product or live-settlement evidence.
