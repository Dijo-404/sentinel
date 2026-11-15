# Sentinel model gateway

Real LLM (Sarvam AI) behind the two existing model contracts. There is no fake or fixture
model in runtime: a missing key, token or knowledge peer stops startup.

| Route                  | Caller                                         | Auth                    |
| ---------------------- | ---------------------------------------------- | ----------------------- |
| `POST /v1/proposals`   | workflow `HttpModelAdapter` (`ModelRequest`)   | `Authorization: Bearer` |
| `POST /v1/replies`     | assistant `HttpModelReply` (`{"text": "..."}`) | none (see below)        |
| `GET /healthz`         | probes                                         | none                    |
| `GET /v1/capabilities` | operators (`financial_authority: false`)       | none                    |

## Proposals: the model proposes, evidence decides

The model returns strict JSON: `outcome`, `transaction_ref`, `amount_minor`, `evidence_ids`,
`reason_codes`. The gateway validates it with pydantic, retries once on malformed output,
then grounds it in `domain/grounding.py`:

- The cited evidence ids must exist and be `VERIFIED`.
- `transaction_ref` must match exactly one verified `PAYMENT` evidence for the case's order,
  `CAPTURED`, in `INR`.
- `amount_minor` must equal the captured amount minus recorded refunds (all statuses except
  `FAILED`), as an integer.
- The proposal's case id, revision, amount, currency and destination are copied from the
  request and evidence. `policy_version` is left out, so the workflow fills its own value.

Any failed rule returns `ESCALATE` with one reason code: `EVIDENCE_ID_INVALID`,
`TRANSACTION_NOT_IN_EVIDENCE`, `ORDER_REFERENCE_MISMATCH`, `PAYMENT_NOT_REFUNDABLE`,
`AMOUNT_NOT_BACKED_BY_EVIDENCE` or `MODEL_OUTPUT_INVALID`. These are HTTP 200 responses, so
the workflow records an escalation rather than retrying.

| Condition                         | Status | Workflow `HttpModelAdapter` maps to |
| --------------------------------- | ------ | ----------------------------------- |
| Grounded proposal or escalation   | 200    | `ModelResult`                       |
| Missing or unknown bearer         | 401    | `PeerError UNAUTHORIZED`            |
| Body is not a `ModelRequest`      | 422    | `PeerError MODEL_ERROR`             |
| Sarvam error, timeout or envelope | 503    | `PeerUnavailableError` (retry)      |

## Replies

The gateway searches knowledge.v1 `GET /v1/search?q=<text>` with
`MODEL_GATEWAY_KNOWLEDGE_TOKEN` and gives the top 5 hits (title and summary) to the model. It
returns `{"text", "evidence_mode": "live"}`. Knowledge or Sarvam failure returns 503. Output
that stays invalid after one retry returns 502. The assistant maps both to
`PeerUnavailableError` and never stores invented text.

`/v1/replies` is unauthenticated because the assistant's `HttpModelReply` sends no bearer
token. Keep the gateway on a private network until that caller sends one. Knowledge results
come from the single tenant of `MODEL_GATEWAY_KNOWLEDGE_TOKEN`.

## Configuration

See [.env.example](.env.example). Required: `SARVAM_API_KEY`, `MODEL_GATEWAY_TOKENS`,
`MODEL_GATEWAY_KNOWLEDGE_URL`, `MODEL_GATEWAY_KNOWLEDGE_TOKEN`.

`MODEL_GATEWAY_REASONING_EFFORT` defaults to `off` (sends `reasoning_effort: null`). Measured
live, sarvam-105b took about 1.3 s per proposal with reasoning off, and 15 to 54 s with
reasoning on. With reasoning on, one call used all 4096 tokens and returned no content. Both
callers use a fixed 10 s timeout, so reasoning on fails as an outage.

Point the callers at the gateway:

```sh
# workflow
WORKFLOW_MODEL_MODE=http
WORKFLOW_PEER_MODEL_URL=http://127.0.0.1:8040
WORKFLOW_OUTBOUND_BEARER=<a token listed in MODEL_GATEWAY_TOKENS>
# assistant
ASSISTANT_MODEL_URL=http://127.0.0.1:8040
```

## Commands

```sh
make -C services/model-gateway check      # ruff + pytest with a controlled Sarvam transport
make -C services/model-gateway preview    # sentinel-model-gateway serve (127.0.0.1:8040)
SARVAM_API_KEY=... make -C services/model-gateway live-test   # real Sarvam calls, opt-in
uv run sentinel-model-gateway serve --host 127.0.0.1 --port 8040
```

A non-loopback `--host` refuses demo bearer tokens such as `tok-workflow`.
