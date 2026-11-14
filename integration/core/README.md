# SN-014 — V1 sandbox assembly harness (`core-assembly.v1`)

Standalone scenario drivers, version/mode configuration and composition adapters for P0 journeys: **pending**, **merchant mismatch**, **duplicate payment**, **refund-pending**, plus authority journeys **browser_to_credit** and **duplicate_approval_deny**.

This module is the **V1 sandbox assembly** entry: fixture self-tests always available; `real-peers` drives HTTP against a local mock payment sandbox (`payment_provider=simulator`). A live provider is a later adapter/credentials swap behind the same `payment-provider.v1` contract — not claimed here.

**Owned root:** `integration/core/` · **Branch:** `feat/v1-assembly-journeys` (historical SN-014: `feat/sn-014-core-integration`)

Contract: `sentinel.task-contracts.v1`, SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.

Produces: `core-assembly.v1`. Consumes: `case-api.v1`, `workflow.v1`, `action-ledger.v1`, `dispatcher.v1`, `verifier.v1`, `payment-provider.v1`, `web-shell.v1`.

## Standalone setup and checks

Requires Python 3.11+, [uv](https://docs.astral.sh/uv/), and GNU Make. No sibling Sentinel service is required for the fixture harness.

```sh
make -C integration/core check
```

Or from this directory:

```sh
make setup
make check
```

`make check` runs Ruff, pytest (journeys, strict assembly negatives, HTTP driver mocks, stub matrix), and `sentinel-core-assembly check`. Fixture self-tests exit 0 on PASS. A separate `real-peers` run exits nonzero on FAIL or UNVERIFIED.

Preview fixture journeys:

```sh
make preview
# or: uv run --frozen sentinel-core-assembly run --mode fixture
```

## Modes

| Mode | Peers | Evidence | MVP claim |
| --- | --- | --- | --- |
| `fixture` | In-process reference peers | Labeled `fixture` | Always `assembled_mvp_claimed=false` |
| `real-peers` | HTTP `/v1/capabilities` + journey drivers | Rejects missing peers, incompatible contract/mode, and `evidence_mode=fixture`; report sets `payment_provider=simulator` | Never auto-claims product release |

Probe rule: every required peer must advertise `mode=real-peers` (including the simulator). Reports still label `payment_provider=simulator` so sandbox is never confused with live rails.

## V1 sandbox

Canonical identity (`tok-*` → principal): [docs/sandbox-matrix.md](docs/sandbox-matrix.md), [fixtures/sandbox-tokens.json](fixtures/sandbox-tokens.json).
Assembly role tokens / journey seeds / path label: [fixtures/sandbox-assembly.json](fixtures/sandbox-assembly.json).
Default real-peers path is `provider-sandbox-only`. Set `SENTINEL_V1_AUTHORITY_PATH=1`
for `browser-to-credit` / SN-009 HTTP journeys (`sn009_authority_exercised=true` when
postconditions pass). Never auto-claims MVP release.

Bring-up (Postgres compose + peer order + assembly command): [docs/sandbox-runbook.md](docs/sandbox-runbook.md).

```sh
docker compose -f compose.yaml up -d
# start peers per runbook (simulator :8094, … web :3012)
make seed-sandbox   # tenant-demo + SENTINEL_V1_SANDBOX; wave0–4 peers seed when DB URLs set
./scripts/run_sandbox_journeys.sh
```

### Wave 0–1 portal peers (merchant / risk) — run order

DB-backed portal checks need Postgres + three peers seeded before verify:

1. Compose Postgres: `docker compose -f compose.yaml up -d` (risk DB is in init SQL; create merchant analytics / disputes DBs per those modules’ `.env.example` if missing).
2. Export sandbox flags + peer DSNs (synthetic only):

```sh
export SENTINEL_V1_SANDBOX=1 CORE_ASSEMBLY_TENANT_ID=tenant-demo
export MERCHANT_ANALYTICS_DATABASE_URL=…   # see services/merchant-analytics/.env.example
export DISPUTES_DATABASE_URL=…             # see services/merchant-disputes/.env.example
export RISK_DATABASE_URL=…                 # see services/risk/.env.example (compose user risk/risk, db risk)
export SENTINEL_API_DATABASE_URL=…         # see apps/api/.env.example (ops escalations/messages/history/audit)
```

3. Seed (orchestrator invokes `make seed` when peer URLs are set; else SKIPPED with the same commands):

```sh
make -C integration/core seed-sandbox
# or manually:
# make -C services/merchant-analytics seed
# make -C services/merchant-disputes seed
# make -C services/risk seed
# make -C apps/api seed
```

4. Serve peers (loopback defaults): analytics `:8032`, disputes `:8030`, risk `:8013` (`make -C <module> preview`).

5. Verify (nonzero if peers down, HTTP ≠ 200, or seed rows missing):

```sh
make -C integration/core verify-wave0-1
# or: ./scripts/verify_wave0_1.sh
```

Asserts HTTP 200 + JSON for:

| Check | Peer URL | Seed marker |
| --- | --- | --- |
| metrics | `GET /v1/merchants/merchant-demo-1/metrics?window_start&window_end` | `merchant_ref=merchant-demo-1` |
| disputes | `GET /v1/merchants/merchant-demo/disputes` | `dispute-seed-demo-1` |
| risk list | `GET /v1/risk/investigations` | `inv-seed-case-demo-42` |

Bearer defaults match module `.env.example` (`operator-token`, `tok-risk-officer`). Override with `VERIFY_*_URL` / `VERIFY_*_TOKEN`.

#### Curl checklist (compose / peers not up)

When the stack is not running, do **not** treat missing peers as pass. Use this checklist after bring-up + seed:

```sh
# analytics (expect 200 JSON with merchant-demo-1; 404 SNAPSHOT_NOT_FOUND = unseeded)
curl -sS -H "Authorization: Bearer operator-token" \
  "http://127.0.0.1:8032/v1/merchants/merchant-demo-1/metrics?window_start=2026-11-01T00:00:00Z&window_end=2026-11-14T00:00:00Z"

# disputes (expect disputes[] containing dispute-seed-demo-1; empty = unseeded)
curl -sS -H "Authorization: Bearer operator-token" \
  "http://127.0.0.1:8030/v1/merchants/merchant-demo/disputes"

# risk (expect investigations[] containing inv-seed-case-demo-42; empty = unseeded)
curl -sS -H "Authorization: Bearer tok-risk-officer" \
  "http://127.0.0.1:8013/v1/risk/investigations"
```

Optional BFF path (web `:3012` + session cookie): `/api/bff/merchant-analytics/...`, `/api/bff/merchant-disputes/...`, `/api/bff/risk/...` — same fail-closed rule; script hits peers directly so web need not be up.

### Wave 2 portal peers (ops case surfaces) — run order

DB-backed ops checks need Postgres + case-api seeded before verify (identity optional):

1. Compose Postgres + `SENTINEL_API_DATABASE_URL` (see Wave 0–1 steps 1–2; include `apps/api` DSN).
2. Seed case-api ops rows (`case-seed-ops-escalated`, `case-seed-ops-history`):

```sh
make -C integration/core seed-sandbox
# or: make -C apps/api seed
```

3. Serve case-api on `:8080` (`make -C apps/api preview`). Optional: identity `:8012` for team.

4. Verify (nonzero if case-api down, HTTP ≠ 200, or seed rows missing):

```sh
make -C integration/core verify-wave2
# or: ./scripts/verify_wave2.sh
```

Asserts HTTP 200 + non-empty seeded JSON for:

| Check | Peer URL | Seed marker |
| --- | --- | --- |
| ESCALATED | `GET /v1/ops/cases?status=ESCALATED` | `case-seed-ops-escalated` |
| HISTORY | `GET /v1/ops/cases?status=HISTORY` | `case-seed-ops-history` |
| messages | `GET /v1/ops/messages` | seed case message present |
| audit-events | `GET /v1/ops/audit-events` | seed case event present |
| team (optional) | `GET /v1/ops/team` | non-empty `members` when `VERIFY_IDENTITY_TOKEN` set |

Bearers: case-api fixtures `token-operator` / `token-supervisor` (override `VERIFY_OPERATOR_TOKEN` / `VERIFY_SUPERVISOR_TOKEN`). Not assembly matrix `tok-operator` (absent from case-api auth map). Identity needs a supervisor **session** from login (`VERIFY_IDENTITY_TOKEN`), not a matrix `tok-*`. Web BFF/pages not required — script hits case-api (+ identity) directly.

#### Curl checklist (wave 2)

```sh
# escalations (expect cases[] containing case-seed-ops-escalated; empty = unseeded)
curl -sS -H "Authorization: Bearer token-operator" \
  "http://127.0.0.1:8080/v1/ops/cases?status=ESCALATED"

# history (expect case-seed-ops-history with CLOSED_NO_ACTION or VERIFIED_RESOLVED)
curl -sS -H "Authorization: Bearer token-supervisor" \
  "http://127.0.0.1:8080/v1/ops/cases?status=HISTORY"

# messages inbox (expect messages[] for seed cases; empty = unseeded)
curl -sS -H "Authorization: Bearer token-operator" \
  "http://127.0.0.1:8080/v1/ops/messages"

# audit events (expect events[] for seed cases; empty = unseeded)
curl -sS -H "Authorization: Bearer token-supervisor" \
  "http://127.0.0.1:8080/v1/ops/audit-events"

# optional team (supervisor session token from identity login)
# curl -sS -H "Authorization: Bearer $VERIFY_IDENTITY_TOKEN" \
#   "http://127.0.0.1:8012/v1/ops/team"
```

### Wave 3 portal peers (identity auth / customer) — run order

DB-backed identity checks need identity seeded before verify:

1. Compose Postgres + `IDENTITY_DATABASE_URL` (see `services/identity/.env.example`), or use fixture mode (`IDENTITY_MODE=fixture`) which seeds principals on serve.
2. Seed identity principals + notification (`customer@example.test`, preferred_language, notification id):

```sh
make -C integration/core seed-sandbox
# or: make -C services/identity seed
```

3. Serve identity on `:8012` (`make -C services/identity preview`).

4. Verify (nonzero if identity down, HTTP ≠ 200, seed rows missing, or forgot enumerates):

```sh
make -C integration/core verify-wave3
# or: ./scripts/verify_wave3.sh
```

Asserts HTTP 200 + seeded JSON for:

| Check | Peer URL | Seed marker |
| --- | --- | --- |
| me | `GET /v1/auth/me` | `customer@example.test` + `preferred_language=en` |
| notifications | `GET /v1/auth/notifications` | `11111111-1111-1111-1111-111111111301` |
| workspaces | `GET /v1/auth/workspaces` | customer workspace present |
| forgot | `POST /v1/auth/password/forgot` | HTTP 202 known+unknown, same public shape |

Session: login with `customer@example.test` + `IDENTITY_DEMO_PASSWORD` (default `x`), or set `VERIFY_IDENTITY_TOKEN` to a hashed **session** from login. Not assembly matrix `tok-customer`. Web BFF/pages not required — script hits identity directly.

### Wave 4 portal peers (intel + voice + approval-ui) — run order

DB-backed intel checks need assistant / knowledge / ops-activity seeded before verify.
Voice capabilities + offline approval-ui package smoke run in the same command.

1. Export sandbox flags + peer DSNs (synthetic only; see each module `.env.example`):

```sh
export SENTINEL_V1_SANDBOX=1 CORE_ASSEMBLY_TENANT_ID=tenant-demo
export ASSISTANT_DATABASE_URL=…
export KNOWLEDGE_DATABASE_URL=…
export OPS_ACTIVITY_DATABASE_URL=…
# optional also: PLATFORM_AI_DATABASE_URL, EVALUATION_DATABASE_URL, OBSERVABILITY_DATABASE_URL
```

2. Seed:

```sh
make -C integration/core seed-sandbox
# or: make -C services/assistant seed && make -C services/knowledge seed && \
#     make -C services/ops-activity seed
```

3. Serve peers (loopback defaults): assistant `:8026`, knowledge `:8035`,
   ops-activity `:8029`, voice `:8017`.

4. Verify (nonzero if peers down, HTTP ≠ 200, or seed rows missing):

```sh
make -C integration/core verify-wave4
# or: ./scripts/verify_wave4.sh
```

Asserts HTTP 200 + seeded JSON for:

| Check | Peer URL | Seed marker |
| --- | --- | --- |
| assistant health | `GET /healthz` | `status=ok` |
| assistant threads | `GET /v1/threads?role=customer` | `thr-seed-tenant-demo` |
| knowledge health | `GET /healthz` | `status=ok` |
| knowledge articles | `GET /v1/articles` | `article-demo-refund-policy` |
| ops-activity health | `GET /healthz` | `status=ok` |
| ops-activity feed | `GET /v1/activity` | `act-seed-case-demo-42` |
| voice capabilities | `GET /v1/capabilities` | `component=voice`, `port=voice.v1` |
| approval-ui package | offline | `packages/approval-ui` exports `ApprovalPanel` |

Tokens default to peer demo maps: `tok-customer` (assistant), `operator-token`
(knowledge + ops-activity). Override with `VERIFY_*_TOKEN` / `VERIFY_*_URL`.

**Documented smoke (module-local, not part of assembly exit):**

```sh
make -C packages/approval-ui check   # Vitest ApprovalPanel
make -C services/voice check         # no Sarvam key required
```

#### Curl checklist (wave 4)

```sh
curl -sS http://127.0.0.1:8026/healthz
curl -sS -H "Authorization: Bearer tok-customer" \
  "http://127.0.0.1:8026/v1/threads?role=customer"

curl -sS http://127.0.0.1:8035/healthz
curl -sS -H "Authorization: Bearer operator-token" \
  http://127.0.0.1:8035/v1/articles

curl -sS http://127.0.0.1:8029/healthz
curl -sS -H "Authorization: Bearer operator-token" \
  http://127.0.0.1:8029/v1/activity

curl -sS http://127.0.0.1:8017/v1/capabilities
```

#### Curl checklist (wave 3)

```sh
# login → session_token (not tok-*)
TOKEN=$(curl -sS -X POST http://127.0.0.1:8012/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"customer@example.test","password":"x"}' | jq -r .session_token)

# me (expect preferred_language=en, display_name=Demo Customer)
curl -sS -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8012/v1/auth/me

# notifications (expect seed notification id; empty = unseeded)
curl -sS -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8012/v1/auth/notifications

# workspaces (expect customer role)
curl -sS -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8012/v1/auth/workspaces

# forgot (expect 202 accepted for both; no existence reveal)
curl -sS -o /dev/null -w '%{http_code}\n' -X POST http://127.0.0.1:8012/v1/auth/password/forgot \
  -H 'Content-Type: application/json' -d '{"email":"customer@example.test"}'
curl -sS -o /dev/null -w '%{http_code}\n' -X POST http://127.0.0.1:8012/v1/auth/password/forgot \
  -H 'Content-Type: application/json' -d '{"email":"nobody-wave3-verify@example.test"}'
```

Optional live pytest (skips unless env set and stack healthy):

```sh
SENTINEL_V1_SANDBOX=1 uv run --frozen pytest tests/test_sandbox_live.py
```

Configuration: [.env.example](.env.example). Contract snapshot: [contracts/core-assembly.v1.json](contracts/core-assembly.v1.json). Hero fixture: [fixtures/duplicate_payment.json](fixtures/duplicate_payment.json) (150000 paise, approval, timeout-after-accept, credit recovery, single side effect).

## Local peer stubs

Under [tests/stubs/](tests/stubs/), each consumed port exposes `valid`, `unavailable`, `malformed`, and `unauthorized_or_out_of_scope`. Fixture-mode journeys use [ReferenceBundle](src/sentinel_core_assembly/adapters/reference.py); [HttpPeerBundle](src/sentinel_core_assembly/adapters/reference.py) never falls back to those stubs on probe or journey failure.

## Layout

```text
integration/core/
  src/sentinel_core_assembly/
    domain/           # journey expectations, RunInput/RunReport
    application/      # assembly runner + ports
    adapters/         # config, composition, matrix, reference + HTTP peers
    cli.py
  compose.yaml        # local Postgres for sandbox peers
  docs/               # sandbox matrix + runbook
  contracts/
  fixtures/
  scripts/run_sandbox_journeys.sh
  scripts/verify_wave0_1.sh
  scripts/verify_wave2.sh
  scripts/verify_wave3.sh
  scripts/verify_wave4.sh
  tests/stubs/
```

## Evidence limits

- Passing `make check` proves the harness, local doubles, and mocked HTTP drivers.
- Live script / `SENTINEL_V1_SANDBOX=1` proves assembly against a running mock sandbox.
- Neither is live-settlement or external pilot evidence.
- Owner-run release selection remains separate (see SN-019).

## Compatibility checklist (real peers)

1. Every required peer URL set; probe `/v1/capabilities`.
2. `contract_version` matches baseline; peer `mode` is `real-peers`.
3. Input artifacts use `evidence_mode=real-component` or `live-provider` — never `fixture`.
4. Report `payment_provider=simulator` for V1 sandbox (live adapter later).
5. Absent/malformed/unauthorized peers surface as FAIL; no silent fixture substitution.
