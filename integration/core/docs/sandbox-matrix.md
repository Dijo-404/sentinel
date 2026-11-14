# Canonical sandbox identity matrix

**Label:** sandbox / synthetic only. No production credentials, no live payments.

**Source of truth:** [../fixtures/sandbox-tokens.json](../fixtures/sandbox-tokens.json)

Use this matrix so local `mode=real-peers` services share one tenant, case, port map, and opaque bearer strings.

## Shared identity

| Field | Value |
| --- | --- |
| `tenant_id` | `tenant-demo` |
| `case_id` | `case-demo-42` |
| `subject_ref` | `subject-demo-42` |
| `merchant_ref` | `merchant-demo-1` |

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
| payment simulator | 8094 |
| web shell | 3012 |

## Shared opaque tokens

Same string is accepted by every peer that needs that role (plus cheap legacy aliases listed in the JSON).

| Token | Typical roles |
| --- | --- |
| `tok-workflow` | workflow service calls |
| `tok-dispatcher` | dispatcher → ledger / provider |
| `tok-verifier` | verifier service calls |
| `tok-case-api` | case API → workflow / peers |
| `tok-customer` | customer UI / case create |
| `tok-supervisor` | approval decisions |
| `tok-sandbox-admin` | simulator admin / demo-reset |

## Module wiring

Each peer's `.env.example` and fixture token map should accept the canonical strings above. Older demo names (`token-workflow-demo`, `workflow-demo-token`, `demo-tenant-a`, `tenant-demo-1`, …) may remain as aliases during transition; new local runs should prefer this matrix.

## Evidence limits

- These tokens are disposable sandbox labels, not secrets of record.
- Passing module checks with this matrix is not assembled product or live-settlement evidence.
