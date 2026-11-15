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

## Invariants

- Evidence/policy network calls happen **before** the reservation transaction. A `ReservationNetworkGuard` fails the TX if a peer call is recorded while the TX is open.
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
