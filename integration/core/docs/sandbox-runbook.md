# V1 sandbox bring-up runbook

Assembles Sentinel against the **mock payment sandbox** (`payment_provider=simulator`).
No production credentials. No real money. Live provider is a later adapter swap.

Canonical identity: [sandbox-matrix.md](sandbox-matrix.md) /
[`fixtures/sandbox-tokens.json`](../fixtures/sandbox-tokens.json) (#84 `tok-*` → principal).
Assembly extras / journey seeds: [`fixtures/sandbox-assembly.json`](../fixtures/sandbox-assembly.json).

## 0. Prerequisites

- Docker (Compose v2), Python 3.11+, `uv`, GNU Make
- Sibling modules checked out on a revision that exposes `/v1/capabilities` with `mode=real-peers`
- Simulator journey packs (#82): `JOURNEY-PENDING`, `JOURNEY-MISMATCH`, `DEMO-ORDER-42`,
  `JOURNEY-REFUND-PENDING` / `refund-pending-1` (fail closed if missing)

## 1. Postgres

From repo root:

```sh
docker compose -f integration/core/compose.yaml up -d
docker compose -f integration/core/compose.yaml ps
```

Creates local databases for api, workflow, ledger, dispatcher, verifier, policy, evidence.
Passwords are demo-only (`sentinel` / per-service users in `compose/init-databases.sql`).

## 2. Peer env (matrix tokens)

Point every peer at the matrix. Minimum shared values:

```sh
export TENANT_ID=tenant-demo
# tokens (same string on every peer that needs the role)
export TOK_WORKFLOW=tok-workflow
export TOK_DISPATCHER=tok-dispatcher
export TOK_VERIFIER=tok-verifier
export TOK_CASE_API=tok-case-api
export TOK_SUPERVISOR=tok-supervisor
export TOK_SANDBOX_ADMIN=tok-sandbox-admin
```

Map each module's `.env` to these (module-specific env names differ; see each README).
Every peer must set its mode env to `real-peers` (e.g. `SIMULATOR_MODE=real-peers`,
`DISPATCHER_MODE=real-peers`, `NEXT_PUBLIC_SHELL_MODE=real-peers`).

## 3. Start services (order)

Start data peers before orchestrators:

| # | Service | Dir | Port | Notes |
| --- | --- | ---: | ---: | --- |
| 1 | Postgres | `integration/core/compose.yaml` | 5432 | step 1 |
| 2 | payment-provider (simulator) | `services/simulator` | 8094 | `mode=real-peers`; demo-reset/seeds |
| 3 | policy | `services/policy` | 8005 | optional for assembly probe; used by ledger |
| 4 | evidence | `services/evidence` | 8006 | optional for probe |
| 5 | action-ledger | `services/action-ledger` | 8009 | migrate then serve |
| 6 | dispatcher | `services/dispatcher` | 8010 | HTTP probe + worker CLI |
| 7 | verifier | `services/verifier` | 8011 | migrate then serve |
| 8 | workflow | `services/workflow` | 8088 | migrate then serve |
| 9 | case-api | `apps/api` | 8080 | migrate then serve |
| 10 | web-shell | `apps/web` | 3012 | `/v1/capabilities` |

Typical pattern per Python service:

```sh
make -C <module> setup
# migrate if the module owns SQL
make -C <module> preview   # or documented serve target
```

## 4. Assembly command

```sh
cd integration/core
cp .env.example .env   # edit if non-default hosts
export CORE_ASSEMBLY_MODE=real-peers
# URLs default from sandbox-assembly.json when mode=real-peers
uv run --frozen sentinel-core-assembly run --mode real-peers \
  --artifact "sandbox-stack,local://v1-sandbox,$(printf '0%.0s' {1..64}),0.1.0,real-component"
```

Or the live script (nonzero exit on failure):

```sh
./scripts/run_sandbox_journeys.sh
```

Optional pytest gate:

```sh
SENTINEL_V1_SANDBOX=1 make check
# or: SENTINEL_V1_SANDBOX=1 uv run --frozen pytest tests/test_sandbox_live.py
```

Fail closed when a full case→workflow→ledger path is required (current drivers are provider-only):

```sh
SENTINEL_V1_REQUIRE_FULL_PATH=1 ./scripts/run_sandbox_journeys.sh  # expected FAIL
```

## 5. Expected report labels

- Peer probes: each required peer `mode=real-peers`
- Report: `payment_provider=simulator`, `path=provider-sandbox-only`,
  `assembled_mvp_claimed=false`, `sn009_authority_exercised=false`
- Journeys: pending → `WAITING_ON_EVIDENCE`; merchant_mismatch → `NEEDS_HUMAN`;
  duplicate_payment → `VERIFIED_RESOLVED` (150000 + timeout recovery + credit);
  refund_pending → `WAITING_ON_PROVIDER` with `credit_confirmed=false`

## 6. Evidence limits

Passing sandbox assembly proves payment-provider HTTP drivers against the mock simulator.
It does **not** exercise SN-009 ledger authority or the full case→workflow→dispatcher path.
It is **not** live-settlement or external pilot acceptance. Fixture `make check` alone
is never product release evidence.
