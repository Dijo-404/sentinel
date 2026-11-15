# model-gateway changelog

## Unreleased

### Added

- Sarvam AI backed gateway (`sentinel-model-gateway serve`, default `127.0.0.1:8040`).
- `POST /v1/proposals` for the workflow `HttpModelAdapter`: bearer-authenticated, returns a
  workflow `ModelResult`. Refund amount, currency and destination are copied from verified
  payment evidence minus recorded refunds. Unbacked amounts, unknown transactions or evidence
  ids, other-order payments and invalid model output return `ESCALATE` with a reason code.
- `POST /v1/replies` for the assistant `HttpModelReply`: grounds the reply in knowledge.v1
  `GET /v1/search` hits and labels it `evidence_mode=live`.
- Strict JSON prompting with pydantic validation, one retry on malformed output, then fail
  closed. Sarvam or knowledge failures return 503.
- Configurable model (`MODEL_GATEWAY_MODEL`, default `sarvam-105b`) and reasoning effort
  (`MODEL_GATEWAY_REASONING_EFFORT`, default `off` to fit the callers' 10s timeouts).
- Unit, contract and fail-closed tests with a controlled Sarvam transport; opt-in live test.
