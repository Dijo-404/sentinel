# SN-010 — Independent refund dispatcher and recovery worker

**State:** implemented. Module-local `make check` is the acceptance command.

**Owned root:** `services/dispatcher/`  
**Package:** `sentinel-dispatcher`  
**Port:** `dispatcher.v1`  
**Branch:** `feat/sn-010-dispatch-recovery`

Contract input: `sentinel.task-contracts.v1` · SHA-256 `0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa`.

## Outcome

Consumes authenticated ledger-issued `Command` values, dispatches only through the configured payment provider using the command's stable `provider_ref` as `Idempotency-Key`, and reports `PENDING` / `OUTCOME_UNKNOWN` / `ESCALATED` outcomes through ledger ports. Durable worker checkpoints survive crash/restart. This module never creates a second authoritative ledger, never mints a new refund ID, and never releases a reservation because a lease expired.

## Standalone setup and checks

Requires Python 3.11+, [uv](https://docs.astral.sh/uv/), GNU Make, and Docker permission to run containers (mandatory PostgreSQL acceptance for durable recovery).

```sh
make -C services/dispatcher setup
make -C services/dispatcher check
```

Or from this directory:

```sh
make setup
make check
```

`uv sync --frozen` installs only this module's locked dependencies. `make check` runs Ruff lint/format checks and pytest. PostgreSQL checks create a private `postgres:17-alpine` container on a random `127.0.0.1` port with tmpfs storage and remove it afterward. Unavailable Docker/PostgreSQL fails the check; there is no in-memory substitute for durable recovery tests.

Local peer doubles live under `tests/stubs/`:

- `action-ledger.v1`: valid, unavailable, malformed, unauthorized_or_out_of_scope
- `payment-provider.v1`: valid, unavailable, malformed, unauthorized_or_out_of_scope, plus commit_then_timeout / ambiguous_not_found fault modes

Evidence mode for `make check`: `payment-provider: simulated stub`, `action-ledger: local stub`, `component-under-test: real` (this package). Sibling Sentinel services are not imported or required.

## Behavior

1. Validate command digest, lease expiry, and refund payload before any provider write.
2. Persist a durable `CLAIMED` checkpoint keyed by `(tenant_id, action_id)` with the original `provider_ref`.
3. Call provider `POST /v1/refunds` with `Idempotency-Key = provider_ref` only.
4. On accept → ledger outcome `PENDING`.
5. On timeout after a possible commit → durable `SUBMITTED` + ledger `OUTCOME_UNKNOWN` (job stays recoverable), then reconcile by original `provider_ref` when `status_lookup` is allowed; terminal `OUTCOME_REPORTED` / `ESCALATED` only after reconcile (or when no safe retry path).
6. On crash/restart → load incomplete jobs (`list_incomplete`) and continue with the same references.
7. Providers without safe same-key retry/status lookup escalate; reservation authority remains with the ledger stub/peer.

## Layout

| Path | Role |
| --- | --- |
| `src/sentinel_dispatcher/domain/` | Digest, validation, recovery decisions (framework-free) |
| `src/sentinel_dispatcher/application/` | `DispatchWorker` use case and ports |
| `src/sentinel_dispatcher/adapters/` | PostgreSQL store, HTTP peer clients, clocks |
| `tests/stubs/` | Ledger and provider doubles |
| `contracts/` | `dispatcher.v1` snapshot and real-peer checklist |
| `migrations/0001_dispatch_jobs.sql` | Owned durable schema |
| `fixtures/demo_command.json` | Baseline claim/refund examples |

## CLI / preview

```sh
uv run --frozen sentinel-dispatcher capabilities
uv run --frozen sentinel-dispatcher migrate   # requires DATABASE_URL
# Real-peer only (no fixture fallback):
# DISPATCHER_MODE=real-peers ... uv run --frozen sentinel-dispatcher run-once
# DISPATCHER_MODE=real-peers ... uv run --frozen sentinel-dispatcher recover
```

See [.env.example](.env.example). Real-peer assembly remains unverified until owner-run integration against live SN-009 / SN-004 components.
