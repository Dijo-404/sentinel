# SN-009 — Authoritative financial action-ledger

**Produces:** `action-ledger.v1`  
**Consumes (local stubs):** `policy.v1`, `evidence.v1`  
**Package:** `sentinel-action-ledger`  
**Contract:** `sentinel.task-contracts.v1` · SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`

Owns approvals, eligibility snapshots, payment reservations, immutable actions, stable provider references, dispatch leases, transactional outbox, and financial audit in one PostgreSQL database. Integer minor units only. All refunds require supervisor approval. Pending provider acceptance is not customer credit.

## Setup

```sh
cd services/action-ledger
make setup          # uv sync --frozen
make check          # ruff + pytest (spins private disposable Postgres via Docker)
```

Optional local Postgres (not required for `make check`):

```sh
docker compose up -d
# set DATABASE_URL from .env.example, then:
make migrate
LEDGER_MODE=fixture  # process boot still needs injected peers; use tests or compose wiring
```

## Routes

| Method | Path                                | Role                                                         |
| ------ | ----------------------------------- | ------------------------------------------------------------ |
| `POST` | `/v1/actions/proposals`             | workflow → `ActionRecord` 201                                |
| `POST` | `/v1/actions/{action_id}/decisions` | supervisor → `Approval`                                      |
| `POST` | `/v1/actions/reservations`          | workflow → `ActionRecord` 201/200 identical retry            |
| `POST` | `/v1/actions/claims`                | dispatcher → `ClaimResult`                                   |
| `GET`  | `/v1/actions/{action_id}`           | workflow, dispatcher, verifier, operator, supervisor         |
| `POST` | `/v1/actions/{action_id}/outcomes`  | dispatcher (accepted/unknown); verifier (evidence-confirmed) |

Also: `/healthz`, `/readyz`, `/v1/capabilities`.

Synthetic bearer tokens are listed in `.env.example` (`token-*-demo`). Body fields never establish identity.

### Portal sessions (optional)

Set `LEDGER_IDENTITY_BASE_URL` (e.g. `http://identity:8012`) to accept web-portal session
bearers forwarded by the web BFF / case-api. Unset or empty keeps static-token-only behaviour.

1. The static token map is checked first; a match never calls identity.
2. Otherwise the ledger calls identity `GET {LEDGER_IDENTITY_BASE_URL}/v1/auth/me` with the same
   bearer (2 s timeout, no cache).
3. Active assignment role `supervisor` → ledger `supervisor`; `operator` → read-only `operator`.
   Every other role → 403. No portal role ever becomes workflow/dispatcher/verifier.
4. `principal_id` = identity `user_id` (recorded as approval `reviewer_id` and audit `actor_id`);
   tenant = active assignment tenant; case/subject scope is tenant-wide (`*`), while decide still
   enforces tenant, digest, case revision, policy version and expiry.
5. The wildcard is granted only when `active_assignment.scope_key` is exactly
   `tenant:<tenant_id>` and `merchant_ref` / `team_id` are null. Merchant- or team-scoped,
   missing, malformed or mismatched-tenant scopes → 403.

Fail closed: identity unreachable/timeout/5xx → 503; identity 401, other non-200 or malformed
body → 401; inactive user, identity 403, revoked/missing assignment, non-tenant-wide scope or
disallowed role → 403.
The non-loopback demo-token bind guard is unchanged.

## Invariants

- Evidence/policy network calls happen **before** the reservation transaction. A `ReservationNetworkGuard` fails the TX if a peer call is recorded while the TX is open.
- The reservation policy recheck receives the stored supervisor approval; the reservation transaction independently validates its binding, digest, revision, policy version and expiry.
- `reserved + pending + refunded ≤ captured` enforced in domain code and a PostgreSQL check constraint; concurrent reservations use `SELECT … FOR UPDATE`.
- Same `operation_key` + identical payload reuses the action (200); different payload → 409.
- Lease expiry does not release money. Only `FAILED_FINAL` with verified evidence releases an allocation.
- `CREDIT_CONFIRMED` requires separate credit evidence after `PROVIDER_CONFIRMED`.

## Local stubs and real peers

| Port          | Fixture                                                                                       | Real-peer adapter    |
| ------------- | --------------------------------------------------------------------------------------------- | -------------------- |
| `policy.v1`   | `tests/stubs/policy.py` (`valid`, `unavailable`, `malformed`, `unauthorized_or_out_of_scope`) | `HttpPolicyClient`   |
| `evidence.v1` | `tests/stubs/evidence.py` (same cases)                                                        | `HttpEvidenceClient` |

`LEDGER_MODE=real-peers` requires `POLICY_BASE_URL` and `EVIDENCE_BASE_URL`. Missing/unauthorized/malformed peers raise visibly; there is no silent fixture fallback.

## Checks and independence

`make check` installs only this module’s lockfile, runs ruff, and pytest against a private Docker Postgres. No sibling Sentinel service source or process is required. Fixture peers cannot satisfy assembled release evidence.

## Layout

```text
src/sentinel_action_ledger/
  domain/           # digest, money, transitions (framework-free)
  application/      # use cases + ports
  adapters/         # HTTP, Postgres, auth, peer clients
  migrations/       # Alembic schema owned solely here
contracts/          # wire snapshots + canonical digest vector
tests/stubs/        # policy + evidence doubles
```
