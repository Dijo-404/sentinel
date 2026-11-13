# SN-021 — Sarvam reasoning and Indic context adapters

Optional `indic-context.v1` adapter: configurable fake/live Sarvam ports, source-preserving Indic/English normalization, structured proposal parsing and safety checks. Models propose only — no financial authority, ledger writes or approvals.

**Owned root:** `packages/indic-context/` · **Branch:** `feat/sn-021-indic-context`

Contract: `sentinel.task-contracts.v1`, SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`. Typed snapshots live in [domain/types.py](src/sentinel_indic_context/domain/types.py); wire contract in [contracts/indic-context.v1.json](contracts/indic-context.v1.json). Consumes nothing. Module-local fixtures under [fixtures/](fixtures/).

## Standalone setup and checks

Requires Python 3.11+, [uv](https://docs.astral.sh/uv/) and GNU Make. From this directory:

```sh
make setup
make check
```

Or from the repository root:

```sh
make -C packages/indic-context check
```

`make check` runs Ruff and pytest in **fake** mode only. No sibling Sentinel service, FinHarness, voice stack or live Sarvam credentials are required. Live provider calls stay opt-in (`INDIC_CONTEXT_MODE=live` plus `INDIC_CONTEXT_SARVAM_API_KEY`); failures never fall back to fixtures.

Root `make check` validates repository metadata. It does not substitute for this module's behavior tests.

## Behavior

| Surface | Role |
| --- | --- |
| `POST /v1/proposals` | `ModelRequest` → `ModelResult` (+ `inference_report`) for workflow callers |
| `FakeSarvamAdapter` | Labeled `fake-inference`; scenarios for proposal / needs_input / escalate / malformed / hallucinated_ref / prompt_injection / unsupported_action / outage |
| `LiveSarvamAdapter` | Opt-in `provider-observation` via Sarvam chat completions; records latency and token cost units |
| Normalization | Tamil/Hindi/English amount, negation, count and reference extraction **without** rewriting `original_text` or `language` |

Safety failures (malformed proposals, hallucinated evidence/transaction refs, prompt injection, unsupported actions) return `outcome=ESCALATE` with explicit reason codes and **no** proposal. Ambiguous amounts return `NEEDS_INPUT`.

Example report fields:

```json
{
  "contract_version": "sentinel.task-contracts.v1",
  "port": "indic-context.v1",
  "evidence_mode": "fake-inference",
  "model_id": "fake-sarvam",
  "latency_ms": 0,
  "cost_units": 0.0,
  "native_review_limit": "human-review-required-for-refunds",
  "outcome": "PROPOSAL",
  "reason_codes": ["DUPLICATE_PAYMENT"]
}
```

## Configuration

See [.env.example](.env.example). Environment files are documentation only. Defaults:

- `INDIC_CONTEXT_MODE=fake`
- `INDIC_CONTEXT_FAKE_SCENARIO=proposal`
- Synthetic bearer map for local demos (never production credentials)

Preview one fixture locally:

```sh
uv run --frozen sentinel-indic-context preview --fixture fixtures/tamil_duplicate.json
```

Serve the HTTP adapter:

```sh
make preview
# or: uv run --frozen sentinel-indic-context serve
```

## Layout

```
src/sentinel_indic_context/
  domain/          # types, normalize, validate, digest (framework-free)
  application/     # ports + propose use case
  adapters/        # fake/live Sarvam, HTTP, auth, settings
fixtures/          # Tamil / Hindi / English / injection evidence fixtures
contracts/         # indic-context.v1 snapshot
tests/             # acceptance, normalization, HTTP, mocked live
```

## Evidence limits

- Standalone `make check` proves fake-mode behavior and mocked live adapter error/reporting paths.
- Real Sarvam account observations, FinHarness assembly and product pilot acceptance are **unverified** here and remain separate owner decisions.
- This package owns no financial tables and cannot authorize refunds.
