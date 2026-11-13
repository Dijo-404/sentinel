# web-shell.v1 compatibility checklist

Contract baseline: `sentinel.task-contracts.v1`  
SHA-256: `0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa`

## Consumed ports

| Port | Fixture location | Real-peer adapter | Notes |
| --- | --- | --- | --- |
| `case-api.v1` | `tests/stubs/case-api/` | `src/adapters/real-peer-case-client.ts` | Required. Failures stay visible. |
| `approval-ui.v1` | `tests/stubs/approval-ui/` | Slot only; no deep import of `packages/approval-ui` | Local substitute in `src/slots/` |
| `voice.v1` | `tests/stubs/voice/` | Optional; disabled by default | Local substitute when enabled |

## Assembly selection

- Fixture mode (`NEXT_PUBLIC_SHELL_MODE=fixture`): local stubs only.
- Real-peer mode (`NEXT_PUBLIC_SHELL_MODE=real-peers`): requires `CASE_API_BASE_URL` + bearer token. Missing/unauthorized/malformed peers raise `PeerError`; no silent fixture fallback.
- Approval UI package may replace `LocalApprovalSubstitute` at assembly via the documented slot props (`ApprovalSlotProps`).
- Voice remains optional and off unless `NEXT_PUBLIC_VOICE_ENABLED=true`.

## Unverified at component PR

- Assembled run against real SN-007 / SN-013 / SN-017 packages.
- Live payment provider or live voice credentials.
