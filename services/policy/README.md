# SN-005 — Standalone deterministic policy service

**State:** implemented. Local `make check` exercises `policy.v1` with fixture principals and evidence only.

**Owned root:** `services/policy/`
**Branch:** `feat/sn-005-policy`
**Produces:** `policy.v1`
**Consumes:** nothing (local proposal/evidence/approval fixtures)

Contract baseline: `sentinel.task-contracts.v1` · SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.

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

Synthetic tokens are in `contracts/principals.json`. Canonical workflow bearer: `tok-workflow` (alias `workflow-demo-token`). Tenant `tenant-demo`. Empty `case_ids` deny; `*` allows all cases (deny-by-default). See `integration/core/docs/sandbox-matrix.md`.

## Routes

| Method | Path               | Auth                                                               | Notes                                                                                                                          |
| ------ | ------------------ | ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------ |
| GET    | `/healthz`         | none                                                               | liveness                                                                                                                       |
| GET    | `/readyz`          | none                                                               | labels `mode`                                                                                                                  |
| GET    | `/v1/capabilities` | none                                                               | `contract_version`, `component=policy`, `mode`                                                                                 |
| GET    | `/v1/policies`     | `platform_admin`, `workflow`, or `sandbox-admin` bearer            | `{ policies: [{ policy_id, version, status, updated_at }] }` seeded with `demo-policy-v1`; read-only catalog, no rule mutation |
| POST   | `/v1/evaluate`     | workflow bearer (ledger may use workflow-scoped service principal) | `PolicyRequest` → `PolicyResult`                                                                                               |

List auth tokens: `tok-platform-admin`, `tok-workflow` / `workflow-demo-token`, `tok-sandbox-admin`. Catalog seed: `contracts/policies.json` (`POLICY_CATALOG_PATH` override).

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
    domain/          # rules + reason codes + PolicyArtifact
    application/     # EvaluatePolicy, ListPolicies + ports
    adapters/        # FastAPI, bearer map, catalog, clocks
    bootstrap.py
  contracts/         # principals, policies seed, request/result snapshots, digest fixture
  tests/unit|contract
```

## Evidence limits

- Standalone fixture check only. Real-peer assembly with live workflow/ledger is unverified here.
- No production credentials, real-money movement, or live payment peers.
- Financial reservation/dispatch remains SN-009/SN-010 authority; this service proposes outcomes only.
