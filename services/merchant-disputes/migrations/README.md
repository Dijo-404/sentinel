# merchant-disputes schema

Owned PostgreSQL schema `merchant_disputes` created by `PostgresDisputeStore.migrate()`
(or `make -C services/merchant-disputes migrate` with `DISPUTES_DATABASE_URL`).

| Table | Purpose |
| --- | --- |
| `disputes` | Dispute cases (tenant/merchant scoped) |
| `evidence_packets` | Assembled packets linked to a dispute |
| `dispute_idempotency` | Create idempotency key → dispute mapping |

Requires `postgresql+psycopg://` (or `postgresql://`) DSN. SQLite remains available for
local fixture/dev via `sqlite:///` URLs.
