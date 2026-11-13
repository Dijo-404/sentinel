# SN-004 — Deterministic payment simulator and fault controls

Synthetic `payment-provider.v1` HTTP service with stable-reference refunds, separate credit evidence, and deterministic fault controls. Local fixture state only; no production payment credentials.

**Owned root:** `services/simulator/` · **Branch:** `feat/sn-004-simulator`

Contract: `sentinel.task-contracts.v1`, SHA-256 `0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa`. Typed route snapshot: [contracts/payment-provider.v1.json](contracts/payment-provider.v1.json). Demo order fixture: [fixtures/demo_order.json](fixtures/demo_order.json).

## Standalone setup and checks

Requires Python 3.11+, [uv](https://docs.astral.sh/uv/), and GNU Make. From this directory:

```sh
make setup
make check
```

Or from the repository root:

```sh
make -C services/simulator check
make check
```

`uv sync --frozen` installs only this module's locked dependencies. `make check` runs Ruff lint/format and pytest. Checks use the in-process FastAPI app and seeded fixture store; no sibling Sentinel service, Docker, or external payment peer is required.

## Seeded hero fixture

On startup the simulator loads:

| Record | Value |
| --- | --- |
| Order | `DEMO-ORDER-42`, `fulfilled_order_count=1`, `merchant_confirmed_duplicate=true`, `paid=true` |
| Payments | `TXN-A` and `TXN-B`, each `CAPTURED` `150000` INR minor units, subject `subject-demo-42` |

Provider refund confirmation and customer credit are separate admin steps / events. A `PROVIDER_CONFIRMED` refund does not imply credit.

## Provider routes (bearer auth)

| Method / route | Roles | Notes |
| --- | --- | --- |
| `GET /healthz`, `GET /readyz` | none | Readiness labels `evidence_mode: fixture` |
| `GET /v1/capabilities` | none | `mode: fixture`, component `sentinel-simulator` |
| `GET /v1/transactions?order_reference=` | workflow, verifier, sandbox-admin | `{ payments: Payment[] }` |
| `GET /v1/orders/{order_reference}` | workflow, verifier, sandbox-admin | `Order` |
| `GET /v1/refunds?transaction_ref=` | workflow, verifier, sandbox-admin | `{ refunds: Refund[] }` |
| `POST /v1/refunds` | dispatcher | Body `RefundRequest`; `Idempotency-Key` must equal `provider_ref`; `202` |
| `GET /v1/refunds/{provider_ref}` | dispatcher, verifier, workflow | Recover after timeout-after-accept; `404` is not proof a write failed |
| `GET /v1/credits/{provider_ref}` | verifier, workflow | Separate credit evidence |

Opaque demo tokens (see [.env.example](.env.example)): `tok-workflow-demo`, `tok-verifier-demo`, `tok-dispatcher-demo`, `tok-sandbox-admin-demo`.

## Fault-control admin routes (`sandbox-admin`)

| Method / route | Behavior |
| --- | --- |
| `GET/PUT /v1/admin/faults` | Schedule: `outage`, `delay_ms`, `timeout_after_accept`, `duplicate_events`, `out_of_order_credit` |
| `POST /v1/admin/faults/reset` | Clear all faults |
| `GET /v1/admin/refunds/{provider_ref}/stats` | `accept_count`, `side_effect_count`, `timeout_count` |
| `POST /v1/admin/refunds/{provider_ref}/confirm` | Set `PROVIDER_CONFIRMED` without credit |
| `POST /v1/admin/credits/{provider_ref}/confirm` | Emit separate confirmed `Credit` |
| `GET /v1/admin/events` | Inspect emitted `REFUND_STATUS` / `CREDIT_STATUS` events |

Fault meanings:

- **outage** — protected routes return `503 PROVIDER_OUTAGE`
- **delay_ms** — sleep before handling
- **timeout_after_accept** — refund side effect persists, response is `504`; recover with `GET /v1/refunds/{provider_ref}`
- **duplicate_events** — confirmation emits two refund status events with distinct `event_id`s
- **out_of_order_credit** — a `CREDIT_STATUS` event is appended before `REFUND_STATUS`; confirmed credit state is still absent until the credit confirm route

## Layout

Clean architecture under `src/sentinel_simulator/`:

- `domain/` — framework-free types and money/idempotency rules
- `application/` — use cases and store port
- `adapters/` — auth token map, in-memory store, HTTP
- `composition/` — FastAPI app factory

## Preview

```sh
make preview
# or: uv run --frozen sentinel-simulator serve --host 127.0.0.1 --port 8094
```

## Evidence mode and assembly limits

Module checks are `evidence_mode: fixture` against this synthetic provider. Assembled product/pilot acceptance that needs real peer wiring remains an owner-run assembly boundary and is unverified here. This module consumes no peers; there is no silent fixture fallback path because the simulator itself is the synthetic provider.
