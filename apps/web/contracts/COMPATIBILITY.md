# web-shell.v1 compatibility checklist

Contract baseline: `sentinel.task-contracts.v1`  
SHA-256: `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`

## Consumed ports

| Port | Fixture location | Real-peer adapter | Notes |
| --- | --- | --- | --- |
| `case-api.v1` | `tests/stubs/case-api/` | `src/adapters/real-peer-case-client.ts` | Required. Failures stay visible. |
| `approval-ui.v1` | `tests/stubs/approval-ui/` + `LocalApprovalSubstitute` | `sentinel-approval-ui` `ApprovalPanel` via `approval-slot` | Real-peers mounts SN-013; decide still via case-api BFF (`props.decide` / `CaseClient.decide`). Fixture keeps local substitute. |
| `voice.v1` | `tests/stubs/voice/` | `real-peer-voice-client.ts` + BFF `/api/bff/voice` → `VOICE_BASE_URL` | Opt-in via `NEXT_PUBLIC_VOICE_ENABLED=true`; label `evidence_mode` recorded vs live |

## Assembly selection

- Fixture mode (`NEXT_PUBLIC_SHELL_MODE=fixture`): local stubs only.
- Real-peer mode (`NEXT_PUBLIC_SHELL_MODE=real-peers`): portal case-api calls go through BFF `/api/bff/case/**` with the per-request `sentinel_session` bearer (never a process-wide portal token in ShellProvider). `CASE_API_BASE_URL` is required server-side; optional `CASE_API_BEARER_TOKEN` is service fallback only. Missing/unauthorized/malformed peers raise `PeerError`; no silent fixture fallback.
- Real-peers approval slot mounts SN-013 `ApprovalPanel` from `sentinel-approval-ui` (`file:../../packages/approval-ui`). Fixture mode keeps `LocalApprovalSubstitute` (`data-slot="approval-ui.v1-local"`). Slot maps `ApprovalSlotProps` → panel props (`caseRecord` → `case`, exact `decisionExpiresAt`, injected `decide`).
- Decide client is always the shell `CaseClient.decide` path (fixture stub or BFF `/api/bff/case` → case-api `POST /v1/ops/actions/{id}/decisions`). The package adapter `createCaseApiDecideClient` is not used from the browser — no direct peer URL/bearer in the slot; package has no money authority.
- Supervisor `/supervisor/approvals` loads the proposal via `CaseClient.getAction` (action-ledger `GET /v1/actions/{id}` through `/api/bff/ledger` in the browser) and decides via case-api as above. Decision expiry is always the earliest evidence `expires_at` (or approval window) in both modes; missing expiry fails closed — no invented calendar constant or silent demo digest. Operator routes and legacy `/ops` evidence do not enable approve controls.
- Voice is optional; product demo sets `NEXT_PUBLIC_VOICE_ENABLED=true`. Real-peers uses BFF → voice peer (fail closed). Fixture mode uses local stub. No SARVAM key required for `make check`.

## Unverified at component PR

- Assembled run against live SN-007 / SN-017 peers. SN-013 `ApprovalPanel` is mounted in real-peers via workspace package build; live case-api decide under session BFF remains assembly-verified separately.
- Live payment provider or live voice credentials.
- Assembled ledger GET against live SN-009 with identity session auth (web BFF `/api/bff/ledger` + `ACTION_LEDGER_BASE_URL`).
