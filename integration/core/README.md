# SN-014 — Four-journey integration harness (`core-assembly.v1`)

Standalone scenario drivers, version/mode configuration and composition adapters for the four P0 journeys: **pending**, **merchant mismatch**, **duplicate payment**, and **refund-pending**. Local reference peers live in-module; strict `real-peers` mode never treats fixture stand-ins as assembled product evidence.

**Owned root:** `integration/core/` · **Branch:** `feat/sn-014-core-integration`

Contract: `sentinel.task-contracts.v1`, SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.

Produces: `core-assembly.v1`. Consumes (local doubles only for self-tests): `case-api.v1`, `workflow.v1`, `action-ledger.v1`, `dispatcher.v1`, `verifier.v1`, `payment-provider.v1`, `web-shell.v1`.

## Standalone setup and checks

Requires Python 3.11+, [uv](https://docs.astral.sh/uv/), and GNU Make. No sibling Sentinel service, shared lockfile, or PostgreSQL is required for the fixture harness.

```sh
make -C integration/core check
```

Or from this directory:

```sh
make setup
make check
```

`make check` runs Ruff, pytest (journeys, strict assembly negatives, stub matrix), and `sentinel-core-assembly check`. Fixture self-tests exit 0 on PASS. A separate `real-peers` run exits nonzero on FAIL or UNVERIFIED.

Preview fixture journeys:

```sh
make preview
# or: uv run --frozen sentinel-core-assembly run --mode fixture
```

## Modes

| Mode | Peers | Evidence | MVP claim |
| --- | --- | --- | --- |
| `fixture` | In-process reference peers | Labeled `fixture` | Always `assembled_mvp_claimed=false` |
| `real-peers` | HTTP `/v1/capabilities` probes from env URLs | Rejects missing peers, incompatible contract/mode, and `evidence_mode=fixture` | Never auto-claims product release |

Configuration: [.env.example](.env.example). Canonical sandbox tenant/token/port matrix: [docs/sandbox-matrix.md](docs/sandbox-matrix.md) ([fixtures/sandbox-tokens.json](fixtures/sandbox-tokens.json)). Contract snapshot: [contracts/core-assembly.v1.json](contracts/core-assembly.v1.json). Hero fixture: [fixtures/duplicate_payment.json](fixtures/duplicate_payment.json) (150000 paise, approval, timeout-after-accept, credit recovery, single side effect).

## Local peer stubs

Under [tests/stubs/](tests/stubs/), each consumed port exposes `valid`, `unavailable`, `malformed`, and `unauthorized_or_out_of_scope`. Fixture-mode journeys use [ReferenceBundle](src/sentinel_core_assembly/adapters/reference.py); the HTTP adapter never falls back to those stubs on probe failure.

## Layout

```text
integration/core/
  src/sentinel_core_assembly/
    domain/           # journey expectations, RunInput/RunReport
    application/      # assembly runner + ports
    adapters/         # config, composition, reference + HTTP peers
    cli.py
  contracts/
  fixtures/
  tests/stubs/
```

## Evidence limits

- Passing `make check` proves the harness and local doubles only.
- It is **not** assembled MVP, pilot, or live-settlement evidence.
- Owner-run assembly selects real component versions and records results separately (see SN-019).

## Compatibility checklist (real peers)

1. Every required peer URL set; probe `/v1/capabilities`.
2. `contract_version` matches baseline; peer `mode` is `real-peers`.
3. Input artifacts use `evidence_mode=real-component` or `live-provider` — never `fixture`.
4. Absent/malformed/unauthorized peers surface as FAIL; no silent fixture substitution.
