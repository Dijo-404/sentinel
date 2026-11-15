# SN-033 — multilingual merchant communications

`merchant-comms.v1`: generate English/Tamil/Hindi merchant or customer status drafts, require an operator approval gate, then record simulated delivery history. Models propose text only — no financial authority, ledger writes or payment credentials.

**Owned root:** `packages/merchant-comms/` · **Branch:** `feat/sn-033-merchant-comms`

Contract: `sentinel.task-contracts.v1`, SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`. Wire type `CommsDraft`. Typed snapshots in [domain/types.py](src/sentinel_merchant_comms/domain/types.py); port contract in [contracts/merchant-comms.v1.json](contracts/merchant-comms.v1.json).

## Standalone setup and checks

Requires Python 3.11+, [uv](https://docs.astral.sh/uv/) and GNU Make. From this directory:

```sh
make setup
make check
```

Or from the repository root:

```sh
make -C packages/merchant-comms check
```

`make check` runs Ruff and pytest using only this module, local fixtures and in-process peer stubs under [tests/stubs/](tests/stubs/). No sibling Sentinel service, payment credentials or live model keys are required.

Root `make check` validates repository metadata. It does not substitute for this module's behavior tests.

## Behavior

| Surface                              | Role                                                               |
| ------------------------------------ | ------------------------------------------------------------------ |
| `POST /v1/drafts`                    | Create `CommsDraft` in `DRAFT` for `en` / `ta` / `hi`              |
| `POST /v1/drafts/{id}/decisions`     | Operator `APPROVE` or `REJECT`                                     |
| `POST /v1/drafts/{id}/simulate-send` | Only after approval → `SIMULATED_SENT` + delivery history          |
| `GET /v1/drafts/{id}`                | Read draft                                                         |
| Optional `indic-context.v1`          | When unavailable/missing → deterministic template labeled `[fake]` |
| Required `case-api.v1`               | Unauthorized / unavailable / malformed → fail closed               |

Preview one lifecycle:

```sh
uv run --frozen sentinel-merchant-comms preview --language ta --no-indic
```

Serve the HTTP adapter:

```sh
make preview
```

## Configuration

See [.env.example](.env.example). Defaults use `MERCHANT_COMMS_MODE=fixture` with labeled local peers. Set `MERCHANT_COMMS_CASE_API_BASE_URL` (and optional Indic URL) for real-peer mode. Real-peer case-api failures never fall back to fixtures.

## Layout

```
src/sentinel_merchant_comms/
  domain/          # CommsDraft types, templates, state transitions
  application/     # ports + draft lifecycle use cases
  adapters/        # HTTP API, auth, fixture peers, real-peer HTTP clients
fixtures/          # synthetic Case + CommsDraft examples
contracts/         # merchant-comms.v1 + consumed peer snapshots
tests/stubs/       # case-api.v1 and indic-context.v1 doubles
```

## Evidence limits

- Standalone `make check` proves approval gate, reject-not-sent, labeled indic fallback and unauthorized fail-closed using fixture peers.
- Real case-api / indic-context assembly, payment-simulator and pilot acceptance remain **unverified** here and are separate owner decisions.
- This package owns no financial tables and cannot authorize refunds.
