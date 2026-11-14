# Knowledge schema migrations

Optional PostgreSQL persistence is owned by this module.

When `KNOWLEDGE_DATABASE_URL` is set, `PostgresArticleStore.migrate()` creates schema
`knowledge` and table:

- `articles` (`tenant_id`, `article_id`, `title`, `summary`, `body`, `updated_at`)

Fixture mode uses `MemoryArticleStore` unless `KNOWLEDGE_DATABASE_URL` is set (then
Postgres). Real-peers mode refuses the default memory store unless a durable store is
injected.

`make seed` requires `KNOWLEDGE_DATABASE_URL` and upserts the sandbox article for
`tenant-demo` (`article-demo-refund-policy`).
