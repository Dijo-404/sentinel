# SN-004 / V1 — Production-shaped mock payment sandbox

Synthetic `payment-provider.v1` HTTP service: stable-reference refunds, separate settlement/credit evidence, signed webhooks, and deterministic fault controls. This is the **mock sandbox** one adapter swap away from a real Paytm provider. Local fixture state only; no production payment credentials.

**Owned root:** `services/simulator/` · **Branch:** `feat/v1-sandbox-simulator` (Refs #79)

Contract: `sentinel.task-contracts.v1`, SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`. Typed route snapshot: [contracts/payment-provider.v1.json](contracts/payment-provider.v1.json). Journey packs: [fixtures/journey_packs.json](fixtures/journey_packs.json).

## Honest labeling

| Field                            | Value                                          |
| -------------------------------- | ---------------------------------------------- |
| `GET /v1/capabilities` `mode`    | `fixture` or `real-peers` via `SIMULATOR_MODE` |
| `GET /readyz` `payment_provider` | always `simulator`                             |
| `GET /readyz` `evidence_mode`    | always `fixture` (synthetic)                   |

`SIMULATOR_MODE=real-peers` lets the assembly probe treat this peer as wired. It does **not** mean live rails. Never claim `live` / Paytm production.

## Standalone setup and checks

Requires Python 3.11+, [uv](https://docs.astral.sh/uv/), and GNU Make. From this directory:

```sh
make setup
make check
```

Or from the repository root:

```sh
make -C services/simulator check
```

## ProviderAdapter surface (Paytm swap target)

Dispatcher, evidence, and verifier talk to this HTTP surface. A future Paytm adapter must implement the same routes/semantics without rewriting ledger or dispatcher rules.

| Method / route                          | Roles                             | Notes                                                              |
| --------------------------------------- | --------------------------------- | ------------------------------------------------------------------ |
| `GET /healthz`, `GET /readyz`           | none                              | Ready labels `payment_provider=simulator`, `evidence_mode=fixture` |
| `GET /v1/capabilities`                  | none                              | `mode: fixture\|real-peers`, component `sentinel-simulator`        |
| `GET /v1/transactions?order_reference=` | workflow, verifier, sandbox-admin | Txn status → `{ payments: Payment[] }`                             |
| `GET /v1/orders/{order_reference}`      | workflow, verifier, sandbox-admin | `Order`                                                            |
| `GET /v1/refunds?transaction_ref=`      | workflow, verifier, sandbox-admin | `{ refunds: Refund[] }`                                            |
| `POST /v1/refunds`                      | dispatcher                        | Body `RefundRequest`; `Idempotency-Key` = `provider_ref`; `202`    |
| `GET /v1/refunds/{provider_ref}`        | dispatcher, verifier, workflow    | Refund status; `404` ≠ write failed                                |
| `GET /v1/credits/{provider_ref}`        | verifier, workflow                | Credit evidence                                                    |
| `GET /v1/settlements/{provider_ref}`    | verifier, workflow                | Settlement evidence (alias of credits)                             |
| `POST /v1/admin/webhooks/emit`          | sandbox-admin                     | Signed webhook envelope for verifier                               |

Opaque demo tokens (see [.env.example](.env.example) and `integration/core/docs/sandbox-matrix.md`): `tok-workflow`, `tok-verifier`, `tok-dispatcher`, `tok-sandbox-admin` (legacy `*-demo` aliases still accepted). Default tenant: `tenant-demo`.

## Journey seed packs

Startup loads all four packs (₹1500 = `150000` INR minor units):

| Pack                | Order                    | Shape                                                                 |
| ------------------- | ------------------------ | --------------------------------------------------------------------- |
| `pending`           | `JOURNEY-PENDING`        | Payment `PENDING`, order unpaid                                       |
| `merchant_mismatch` | `JOURNEY-MISMATCH`       | Payment `CAPTURED`, order `paid=false`                                |
| `duplicate_payment` | `DEMO-ORDER-42`          | Two `CAPTURED` `TXN-A`/`TXN-B` @ 150000; merchant duplicate confirmed |
| `refund_pending`    | `JOURNEY-REFUND-PENDING` | Captured payment + seeded refund `refund-pending-1` `PENDING`         |

```sh
# Against a running preview (:8094)
uv run --frozen sentinel-simulator seed pending
uv run --frozen sentinel-simulator seed merchant_mismatch
uv run --frozen sentinel-simulator seed duplicate_payment
uv run --frozen sentinel-simulator seed refund_pending
# or admin:
curl -X POST -H "Authorization: Bearer tok-sandbox-admin" \
  http://127.0.0.1:8094/v1/admin/seeds/duplicate_payment
```

## Fault schedules

| Schedule               | Effect                                                                                    |
| ---------------------- | ----------------------------------------------------------------------------------------- |
| `timeout-after-accept` | Refund side effect persists; response `504`; recover via `GET /v1/refunds/{provider_ref}` |
| `duplicate-webhook`    | Confirmation emits two refund status events (`duplicate_events`)                          |
| `out-of-order`         | Credit-looking event before refund confirmation; credit state still absent                |

```sh
uv run --frozen sentinel-simulator fault timeout-after-accept
uv run --frozen sentinel-simulator fault duplicate-webhook
uv run --frozen sentinel-simulator fault out-of-order
# or:
curl -X POST -H "Authorization: Bearer tok-sandbox-admin" \
  http://127.0.0.1:8094/v1/admin/faults/schedules/timeout-after-accept
```

Aliases on `PUT /v1/admin/faults`: `duplicate_webhook` → `duplicate_events`, `out_of_order` → `out_of_order_credit`.

## demo-reset (sandbox tenant only)

Requires `SIMULATOR_SANDBOX=true` on the server **and** principal `tenant_id=tenant-demo`. Other tenants / missing sandbox flag → refuse.

```sh
export SIMULATOR_SANDBOX=true
make preview   # separate terminal
uv run --frozen sentinel-simulator demo-reset
# or:
curl -X POST -H "Authorization: Bearer tok-sandbox-admin" \
  http://127.0.0.1:8094/v1/admin/demo-reset
```

## Shared HMAC for verifier webhooks

Set the same secret on simulator and verifier:

| Env                          | Owner               |
| ---------------------------- | ------------------- |
| `SIMULATOR_WEBHOOK_HMAC_KEY` | this module         |
| `VERIFIER_WEBHOOK_HMAC_KEY`  | `services/verifier` |

Signing: lowercase hex HMAC-SHA256 over **original JSON bytes** → header `X-Sentinel-Signature`. Demo default `demo-simulator-hmac-key` is synthetic only.

```sh
curl -X POST -H "Authorization: Bearer tok-sandbox-admin" \
  -H "Content-Type: application/json" \
  -d '{"provider_ref":"refund-pending-1","type":"REFUND_STATUS"}' \
  http://127.0.0.1:8094/v1/admin/webhooks/emit
```

POST the returned `raw_body` + `headers.X-Sentinel-Signature` to verifier `POST /v1/webhooks/simulator`.

## Fault-control admin routes (`sandbox-admin`)

| Method / route                                  | Behavior                                                                                                      |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| `GET/PUT /v1/admin/faults`                      | Schedule: `outage`, `delay_ms`, `timeout_after_accept`, `duplicate_events`, `out_of_order_credit` (+ aliases) |
| `POST /v1/admin/faults/reset`                   | Clear all faults                                                                                              |
| `POST /v1/admin/faults/schedules/{name}`        | Named journey fault packs                                                                                     |
| `POST /v1/admin/seeds/{pack}`                   | Replace store with one journey pack                                                                           |
| `POST /v1/admin/demo-reset`                     | Restore all packs; sandbox + `tenant-demo` only                                                               |
| `POST /v1/admin/webhooks/emit`                  | Signed webhook envelope                                                                                       |
| `GET /v1/admin/refunds/{provider_ref}/stats`    | `accept_count`, `side_effect_count`, `timeout_count`                                                          |
| `POST /v1/admin/refunds/{provider_ref}/confirm` | Set `PROVIDER_CONFIRMED` without credit                                                                       |
| `POST /v1/admin/credits/{provider_ref}/confirm` | Emit separate confirmed `Credit`                                                                              |
| `GET /v1/admin/events`                          | Inspect emitted `REFUND_STATUS` / `CREDIT_STATUS` events                                                      |

## Preview

```sh
export SIMULATOR_MODE=real-peers SIMULATOR_SANDBOX=true
make preview
# or: uv run --frozen sentinel-simulator serve --host 127.0.0.1 --port 8094
```

## Evidence mode and assembly limits

Module checks are `evidence_mode: fixture` / `payment_provider: simulator`. Assembled product/pilot acceptance that needs real peer wiring remains an owner-run assembly boundary and is unverified here. A Paytm credential swap is a separate owner decision; this module never holds production payment secrets.
