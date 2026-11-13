# SN-011 — Independent webhook and verification service

**State:** implemented. Module-local `make check` is the acceptance command.

**Owned root:** `services/verifier/`  
**Package:** `sentinel-verifier`  
**Port:** `verifier.v1`  
**Branch:** `feat/sn-011-verification`

Contract input: `sentinel.task-contracts.v1` · SHA-256 `0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa`.

## Outcome

Owns verified webhook inbox, scheduled rechecks, and closure assessment. Uses independent migrations and local provider/ledger/evidence/case-api stubs. Sends authenticated evidence to ledger outcome APIs — never edits ledger tables. Pending refund is not customer credit; provider confirmation and credit confirmation stay distinct.

## Standalone setup and checks

Requires Python 3.11+, [uv](https://docs.astral.sh/uv/), GNU Make, and Docker permission to run containers (mandatory PostgreSQL acceptance for durable inbox).

```sh
make -C services/verifier setup
make -C services/verifier check
```

Or from this directory:

```sh
make setup
make check
```

`uv sync --frozen` installs only this module's locked dependencies. `make check` runs Ruff lint/format checks and pytest. PostgreSQL checks create a private `postgres:17-alpine` container on a random `127.0.0.1` port with tmpfs storage and remove it afterward. Unavailable Docker/PostgreSQL fails the check; durable inbox tests do not substitute an in-memory store for those proofs.

Local peer doubles live under `tests/stubs/`:

- `payment-provider.v1`: valid, unavailable, malformed, unauthorized_or_out_of_scope
- `action-ledger.v1`: valid, unavailable, malformed, unauthorized_or_out_of_scope
- `evidence.v1`: valid, unavailable, malformed, unauthorized_or_out_of_scope
- `case-api.v1`: valid, unavailable, malformed, unauthorized_or_out_of_scope

Evidence mode for `make check`: peers are local stubs; component-under-test is this package. Sibling Sentinel services are not imported or required.

## Behavior

1. `POST /v1/webhooks/simulator` verifies `X-Sentinel-Signature` as lowercase hex HMAC-SHA256 over **original bytes**, maps `merchant_ref` → tenant, applies replay/age policy, then commits the durable inbox before 202 `{accepted:true}`.
2. Duplicate `event_id` per tenant skips only when already `PROCESSED`; an `ACCEPTED` (crash-after-insert) duplicate re-runs reconciliation. Out-of-order events reconcile **current** provider status by stable `provider_ref` (event type alone never confirms).
3. `POST /v1/rechecks` schedules a durable job (`Idempotency-Key` required) and binds `provider_ref` → action/case scope. `POST /v1/rechecks/drain` (or `sentinel-verifier drain-rechecks` / `VerifierService.drain_due_rechecks`) claims due `SCHEDULED` or lease-expired jobs and reconciles.
4. `POST /v1/assessments` classifies WAITING / VERIFIED / CONFLICT / ESCALATED; posts ledger outcomes only for evidence-backed transitions; announces case results only after credit-confirmed VERIFIED assessments. PENDING refund evidence is `UNVERIFIED`; terminal provider statuses are `VERIFIED`.
5. Unknown/pending outcomes retain reservations; only authoritative final failure or credit confirmation releases via ledger APIs.
6. Real-peers mode refuses demo webhook HMAC (`demo-simulator-hmac-key`) and demo bearer (`token-verifier-demo`). Fixture/test mode may keep demos. Empty `case_ids` deny; `"*"` allows all.

## Layout

| Path | Role |
| --- | --- |
| `src/sentinel_verifier/domain/` | Signature, assessment rules, wire types |
| `src/sentinel_verifier/application/` | `VerifierService` use cases and ports |
| `src/sentinel_verifier/adapters/` | FastAPI, PostgreSQL store, HTTP peers, auth |
| `tests/stubs/` | Provider, ledger, evidence, case-api doubles |
| `contracts/` | `verifier.v1` snapshot and real-peer checklist |
| `migrations/0001_verifier.sql` | Owned durable schema |
| `fixtures/` | Demo webhook and verification request |

## CLI / preview

```sh
uv run --frozen sentinel-verifier capabilities
uv run --frozen sentinel-verifier migrate   # requires DATABASE_URL
uv run --frozen sentinel-verifier drain-rechecks   # claim due rechecks (real-peers env)
make preview   # uvicorn on 127.0.0.1:8011 (requires env + peers for real mode)
```

See [.env.example](.env.example). Real-peer assembly remains unverified until owner-run integration against live SN-004 / SN-005 / SN-008 / SN-009 components.
