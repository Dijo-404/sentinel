# platform-ai changelog

## Unreleased

### Added

- Independent `platform-ai.v1` HTTP+Postgres peer on port `8036`
  (8030 stays merchant-disputes).
- `GET /v1/config` → `{ models, kill_switch, updated_at }` (metadata only).
- `GET /v1/runs` → `{ runs: [{ run_id, model_id, status, started_at }] }`.
- `GET /v1/integrations` → `{ integrations: [{ integration_id, name, status, updated_at }] }`.
- Schema `platform_ai.ai_configs` / `ai_runs` / `ai_integrations`; `make seed`
  writes one synthetic config + run + integration for `tenant-demo`.
- `/healthz`, `/readyz`, `/v1/capabilities` with `money_authority: false`.
- real-peers requires `PLATFORM_AI_DATABASE_URL`; no silent memory fallback.
