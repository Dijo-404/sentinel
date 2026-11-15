# platform-ai — admin AI config and run metadata

Independent `platform-ai.v1` HTTP service: tenant AI model config and run
metadata for admin surfaces. **No money authority.** Never calls ledger decide
or stores amount/refund/payment fields.

**Owned root:** `services/platform-ai/`  
**Default port:** `8036`  
**Branch:** `feat/portal-wave4-intel-voice-approval`

Contract: `sentinel.task-contracts.v1`, SHA-256
`0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.
Typed snapshot: [contracts/platform-ai.v1.json](contracts/platform-ai.v1.json).

## Routes

| Method | Path | Roles | Response |
| --- | --- | --- | --- |
| `GET` | `/v1/config` | platform_admin, sandbox-admin | `{ models, kill_switch, updated_at }` |
| `GET` | `/v1/runs` | platform_admin, sandbox-admin | `{ runs: [{ run_id, model_id, status, started_at }] }` |
| `GET` | `/v1/integrations` | platform_admin, sandbox-admin | `{ integrations: [{ integration_id, name, status, updated_at }] }` |

Also: `/healthz`, `/readyz`, `/v1/capabilities` (`mode: fixture|real-peers`,
`money_authority: false`).

## Setup and check

Requires Python 3.11+, [uv](https://docs.astral.sh/uv/), GNU Make, Docker
(for Postgres proofs in `make check`).

```sh
make -C services/platform-ai check
```

Runs lockfile sync, ruff, then pytest (memory API + disposable Docker Postgres
seed proofs). Observed mode for unit HTTP tests: `fixture`.

## Run locally

```sh
cp services/platform-ai/.env.example services/platform-ai/.env
make -C services/platform-ai preview
# listens on PLATFORM_AI_HOST/PLATFORM_AI_PORT (default 127.0.0.1:8036)

make -C services/platform-ai seed
# requires PLATFORM_AI_DATABASE_URL; writes tenant-demo config + run + integration
```

Synthetic bearer: `admin-token` (platform_admin / tenant-demo).

## Layout

```text
services/platform-ai/
  src/sentinel_platform_ai/
    domain/            # AiConfig, AiRun, AiIntegration, Principal
    application/       # service + ports
    adapters/          # FastAPI, auth, memory/postgres stores
    bootstrap.py
    seed.py
    cli.py
  contracts/           # platform-ai.v1.json
  fixtures/            # config_demo.json, run_demo.json, integration_demo.json
  migrations/          # 0001_platform_ai.sql
  tests/
```

## Modes

| Mode | How | Notes |
| --- | --- | --- |
| `fixture` (default) | in-memory store | used by `make check` unit HTTP tests |
| `real-peers` | `PLATFORM_AI_MODE=real-peers` + `PLATFORM_AI_DATABASE_URL` | refuses missing DSN; never silent memory fallback |

## Evidence limits

- Standalone module check only. Portal Admin → AI wiring is a later wave task.
- Seed data is synthetic sandbox (`tenant-demo`). No live model provider calls.
- No payment credentials, ledger writes, or money fields on the wire.
