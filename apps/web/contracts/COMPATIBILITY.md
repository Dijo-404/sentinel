# web-shell.v1 compatibility checklist

Contract baseline: `sentinel.task-contracts.v1`  
SHA-256: `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`

## Consumed ports

| Port | Fixture location | Real-peer adapter | Notes |
| --- | --- | --- | --- |
| `case-api.v1` | `tests/stubs/case-api/` | `src/adapters/real-peer-case-client.ts` | Required. Failures stay visible. |
| `approval-ui.v1` | `tests/stubs/approval-ui/` | Slot only; no deep import of `packages/approval-ui` | Local substitute in `src/slots/` |
| `voice.v1` | `tests/stubs/voice/` | Optional; disabled by default | Local substitute when enabled |

## Assembly selection

- Fixture mode (`NEXT_PUBLIC_SHELL_MODE=fixture`): local stubs only.
- Real-peer mode (`NEXT_PUBLIC_SHELL_MODE=real-peers`): portal case-api calls go through BFF `/api/bff/case/**` with the per-request `sentinel_session` bearer (never a process-wide portal token in ShellProvider). `CASE_API_BASE_URL` is required server-side; optional `CASE_API_BEARER_TOKEN` is service fallback only. Missing/unauthorized/malformed peers raise `PeerError`; no silent fixture fallback.
- Approval UI package may replace `LocalApprovalSubstitute` at assembly via the documented slot props (`ApprovalSlotProps` including exact `decisionExpiresAt`).
- Supervisor `/supervisor/approvals` embeds the slot with case-api `decide` (`POST /v1/ops/actions/{id}/decisions`). Operator routes and legacy `/ops` evidence do not enable approve controls.
- Voice remains optional and off unless `NEXT_PUBLIC_VOICE_ENABLED=true`.

## Unverified at component PR

- Assembled run against real SN-007 / SN-013 / SN-017 packages.
- Live payment provider or live voice credentials.
- Supervisor action GET / ledger-backed decision expiry (fixture uses `FIXTURE_DECISION_EXPIRES_AT`).
