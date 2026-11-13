# SN-005 — Standalone deterministic policy service

**State:** implemented. Local `make check` exercises `policy.v1` with fixture principals and evidence only.

**Owned root:** `services/policy/`
**Branch:** `feat/sn-005-policy`
**Produces:** `policy.v1`
**Consumes:** nothing (local proposal/evidence/approval fixtures)

Contract baseline: `sentinel.task-contracts.v1` · SHA-256 `0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa`.

## Outcome

`POST /v1/evaluate` accepts `PolicyRequest` under an opaque bearer → `Principal` and returns `PolicyResult` with `ALLOW`, `REQUIRE_APPROVAL`, `DENY`, or `NEED_EVIDENCE`. Rules live in framework-free domain code (`demo-policy-v1`). HTTP and token maps stay in adapters.

## Setup and check

Requires `uv` on PATH. No sibling Sentinel service, shared lockfile, or PostgreSQL.

```sh
make -C services/policy check
```

This syncs the module lockfile, runs ruff, then pytest (unit + HTTP contract). Observed mode: `fixture`.

## Run locally

```sh
cp services/policy/.env.example services/policy/.env   # optional documentation only
make -C services/policy preview
# listens on POLICY_HOST/POLICY_PORT (default 127.0.0.1:8005)
```

Synthetic tokens are in `contracts/principals.json`. Example workflow bearer: `workflow-demo-token`. Empty `case_ids` deny; `*` allows all cases (deny-by-default).

## Routes

| Method | Path | Auth | Notes |
| --- | --- | --- | --- |
| GET | `/healthz` | none | liveness |
| GET | `/readyz` | none | labels `mode` |
| GET | `/v1/capabilities` | none | `contract_version`, `component=policy`, `mode` |
| POST | `/v1/evaluate` | workflow bearer (ledger may use workflow-scoped service principal) | `PolicyRequest` → `PolicyResult` |

## Rules summary (`demo-policy-v1`)

Refunds (`REQUEST_REFUND`):

- Authenticated `workflow` role; case and subject must match principal scope (wrong tenant/case → `TENANT_SCOPE_DENIED`).
- Destination must be `ORIGINAL_PAYMENT_ROUTE`; excess amount and non-captured/pending/failed payments deny with reason codes.
- Fresh `VERIFIED` payment + order evidence required; expired/unverified → `NEED_EVIDENCE`; fraud/chargeback sources → `DENY`.
- Merchant confirmation required for the duplicate-payment hero path.
- All refunds need an unexpired `APPROVE` approval bound to exact digest, revision, and policy version. Missing/expired/mismatched → `REQUIRE_APPROVAL`. `REJECT` → `DENY`.
- Undeclared body/payload fields (model/customer text) are rejected at parse time; they cannot mint an approval.

Canonical action digest matches the baseline fixture in `contracts/digest-fixture.json`.

## Layout

```text
services/policy/
  src/sentinel_policy/
    domain/          # rules + reason codes
    application/     # EvaluatePolicy + Clock port
    adapters/        # FastAPI, bearer map, clocks
    bootstrap.py
  contracts/         # principals, request/result snapshots, digest fixture
  tests/unit|contract
```

## Evidence limits

- Standalone fixture check only. Real-peer assembly with live workflow/ledger is unverified here.
- No production credentials, real-money movement, or live payment peers.
- Financial reservation/dispatch remains SN-009/SN-010 authority; this service proposes outcomes only.
