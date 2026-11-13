# workflow schema

Module-owned tables live in PostgreSQL schema `workflow`:

- `jobs` — `job_key` idempotency and thread binding
- `result_outbox` — durable case-result delivery with retries
- `decisions` — authenticated approval resume payloads

LangGraph checkpoint tables are created by `PostgresSaver.setup()` in the same database.

Apply with:

```sh
uv run sentinel-workflow migrate
```

Tests start a disposable Docker PostgreSQL and apply the same schema.
