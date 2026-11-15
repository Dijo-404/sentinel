# Knowledge schema migrations

PostgreSQL persistence is owned by this module. The server must ship `pgvector` >= 0.8
(deploy image `pgvector/pgvector:pg17`).

`PostgresArticleStore.migrate()` (run by `serve`, `seed` and `reindex`) is idempotent:

```sql
CREATE EXTENSION IF NOT EXISTS vector;            -- fails closed if unavailable
CREATE SCHEMA IF NOT EXISTS knowledge;
CREATE TABLE IF NOT EXISTS knowledge.articles (...);  -- tenant_id, article_id PK
ALTER TABLE knowledge.articles
  ADD COLUMN IF NOT EXISTS embedding vector(<model dims>),
  ADD COLUMN IF NOT EXISTS embedding_model varchar(256);
CREATE INDEX IF NOT EXISTS articles_embedding_hnsw
  ON knowledge.articles USING hnsw (embedding vector_cosine_ops);
```

Existing pre-pgvector rows get the new nullable columns; `serve` startup and
`sentinel-knowledge reindex` embed every row whose vector is missing or was produced by a
different model. If the configured model's dimension differs from the column, `serve`
refuses to start; `sentinel-knowledge reindex` drops and recreates the column (and HNSW
index) at the new dimension, then re-embeds all rows.

Fixture mode uses `MemoryArticleStore` (substring search) unless
`KNOWLEDGE_DATABASE_URL` is set (then Postgres + pgvector). Real-peers mode refuses the
memory store unless a durable store is injected.

`make seed` requires `KNOWLEDGE_DATABASE_URL` and upserts (and embeds) the sandbox
article for `tenant-demo` (`article-demo-refund-policy`).
