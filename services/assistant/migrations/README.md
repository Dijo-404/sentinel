# Assistant schema migrations

Optional PostgreSQL persistence is owned by this module.

When `ASSISTANT_DATABASE_URL` is set, `PostgresAssistantStore.migrate()` creates schema `assistant` and tables:

- `assistant_threads`
- `assistant_messages`

Fixture mode uses `MemoryAssistantStore` unless `ASSISTANT_DATABASE_URL` is set (then Postgres). Real-peers mode refuses the default memory store unless a durable store is injected.

`make seed` requires `ASSISTANT_DATABASE_URL` and upserts the sandbox thread + messages for `tenant-demo`.
