# assistant.v1 — threads and sandbox messages

Standalone assistant service: persisted customer/operator threads and messages. Models propose text only; this peer has **no** payment or ledger authority.

**Owned root:** `services/assistant/` · **Preview port:** `8026`

Contract snapshot: `contracts/assistant.v1.json` (`assistant.v1`).

## Standalone setup and checks

```sh
make -C services/assistant check
```

Installs only this module's `uv` dependencies (`pyproject.toml` / `uv.lock`). Fixture tests use an in-memory store. PostgreSQL via `ASSISTANT_DATABASE_URL` is required for `make seed` and durable real-peers state.

Preview (fixture mode, port **8026**):

```sh
cp services/assistant/.env.example services/assistant/.env
# optional: export $(grep -v '^#' services/assistant/.env | xargs)
make -C services/assistant preview
```

Sandbox seed (≥1 thread + messages for `tenant-demo`):

```sh
# ASSISTANT_DATABASE_URL must point at Postgres
make -C services/assistant seed
```

Stable seed ids: `thr-seed-tenant-demo`, `msg-seed-tenant-demo-user`, `msg-seed-tenant-demo-assistant`. Evidence label: synthetic-sandbox (`evidence_mode=sandbox`). Idempotent upsert.

## Routes

| Method | Path                                  | Auth   | Notes                                                                    |
| ------ | ------------------------------------- | ------ | ------------------------------------------------------------------------ |
| GET    | `/v1/health`                          | none   | liveness                                                                 |
| GET    | `/healthz`                            | none   | peer-style liveness                                                      |
| GET    | `/readyz`                             | none   | labels `mode`                                                            |
| GET    | `/v1/capabilities`                    | none   | `financial_authority=false`                                              |
| GET    | `/v1/threads?role=customer\|operator` | bearer | tenant-scoped list                                                       |
| POST   | `/v1/threads`                         | bearer | optional `{ title }`                                                     |
| GET    | `/v1/threads/{id}/messages`           | bearer | tenant-scoped                                                            |
| POST   | `/v1/threads/{id}/messages`           | bearer | `{ text }` → user message + assistant reply (sandbox echo or `ASSISTANT_MODEL_URL`) |

## Auth

`ASSISTANT_TOKENS` opaque map: `token=principal_id|tenant_id|roles` (`;`-separated entries). Tenant comes from the token map, never from client-supplied headers alone.

## Real-peer mode

Set `ASSISTANT_MODE=real-peers` and `ASSISTANT_DATABASE_URL` (or inject a durable store). Missing durable store surfaces as an error; memory is never substituted silently.

## Layout

```text
services/assistant/
  src/sentinel_assistant/
    domain/
    application/
    adapters/
    bootstrap.py
    seed.py
    cli.py
  contracts/assistant.v1.json
  migrations/
  tests/
```
