# SN-014 — V1 sandbox assembly harness (`core-assembly.v1`)

Standalone scenario drivers, version/mode configuration and composition adapters for P0 journeys: **pending**, **merchant mismatch**, **duplicate payment**, **refund-pending**, plus authority journeys **browser_to_credit** and **duplicate_approval_deny**.

This module is the **V1 sandbox assembly** entry: fixture self-tests always available; `real-peers` drives HTTP against a local mock payment sandbox (`payment_provider=simulator`). A live provider is a later adapter/credentials swap behind the same `payment-provider.v1` contract — not claimed here.

**Owned root:** `integration/core/` · **Branch:** `feat/v1-assembly-journeys` (historical SN-014: `feat/sn-014-core-integration`)

Contract: `sentinel.task-contracts.v1`, SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.

Produces: `core-assembly.v1`. Consumes: `case-api.v1`, `workflow.v1`, `action-ledger.v1`, `dispatcher.v1`, `verifier.v1`, `payment-provider.v1`, `web-shell.v1`.

## Standalone setup and checks

Requires Python 3.11+, [uv](https://docs.astral.sh/uv/), and GNU Make. No sibling Sentinel service is required for the fixture harness.

```sh
make -C integration/core check
```

Or from this directory:

```sh
make setup
make check
```

`make check` runs Ruff, pytest (journeys, strict assembly negatives, HTTP driver mocks, stub matrix), and `sentinel-core-assembly check`. Fixture self-tests exit 0 on PASS. A separate `real-peers` run exits nonzero on FAIL or UNVERIFIED.

Preview fixture journeys:

```sh
make preview
# or: uv run --frozen sentinel-core-assembly run --mode fixture
```

## Modes

| Mode | Peers | Evidence | MVP claim |
| --- | --- | --- | --- |
| `fixture` | In-process reference peers | Labeled `fixture` | Always `assembled_mvp_claimed=false` |
| `real-peers` | HTTP `/v1/capabilities` + journey drivers | Rejects missing peers, incompatible contract/mode, and `evidence_mode=fixture`; report sets `payment_provider=simulator` | Never auto-claims product release |

Probe rule: every required peer must advertise `mode=real-peers` (including the simulator). Reports still label `payment_provider=simulator` so sandbox is never confused with live rails.

## V1 sandbox

Canonical identity (`tok-*` → principal): [docs/sandbox-matrix.md](docs/sandbox-matrix.md), [fixtures/sandbox-tokens.json](fixtures/sandbox-tokens.json).
Assembly role tokens / journey seeds / path label: [fixtures/sandbox-assembly.json](fixtures/sandbox-assembly.json).
Default real-peers path is `provider-sandbox-only`. Set `SENTINEL_V1_AUTHORITY_PATH=1`
for `browser-to-credit` / SN-009 HTTP journeys (`sn009_authority_exercised=true` when
postconditions pass). Never auto-claims MVP release.

Bring-up (Postgres compose + peer order + assembly command): [docs/sandbox-runbook.md](docs/sandbox-runbook.md).

```sh
docker compose -f compose.yaml up -d
# start peers per runbook (simulator :8094, … web :3012)
./scripts/run_sandbox_journeys.sh
```

Optional live pytest (skips unless env set and stack healthy):

```sh
SENTINEL_V1_SANDBOX=1 uv run --frozen pytest tests/test_sandbox_live.py
```

Configuration: [.env.example](.env.example). Contract snapshot: [contracts/core-assembly.v1.json](contracts/core-assembly.v1.json). Hero fixture: [fixtures/duplicate_payment.json](fixtures/duplicate_payment.json) (150000 paise, approval, timeout-after-accept, credit recovery, single side effect).

## Local peer stubs

Under [tests/stubs/](tests/stubs/), each consumed port exposes `valid`, `unavailable`, `malformed`, and `unauthorized_or_out_of_scope`. Fixture-mode journeys use [ReferenceBundle](src/sentinel_core_assembly/adapters/reference.py); [HttpPeerBundle](src/sentinel_core_assembly/adapters/reference.py) never falls back to those stubs on probe or journey failure.

## Layout

```text
integration/core/
  src/sentinel_core_assembly/
    domain/           # journey expectations, RunInput/RunReport
    application/      # assembly runner + ports
    adapters/         # config, composition, matrix, reference + HTTP peers
    cli.py
  compose.yaml        # local Postgres for sandbox peers
  docs/               # sandbox matrix + runbook
  contracts/
  fixtures/
  scripts/run_sandbox_journeys.sh
  tests/stubs/
```

## Evidence limits

- Passing `make check` proves the harness, local doubles, and mocked HTTP drivers.
- Live script / `SENTINEL_V1_SANDBOX=1` proves assembly against a running mock sandbox.
- Neither is live-settlement or external pilot evidence.
- Owner-run release selection remains separate (see SN-019).

## Compatibility checklist (real peers)

1. Every required peer URL set; probe `/v1/capabilities`.
2. `contract_version` matches baseline; peer `mode` is `real-peers`.
3. Input artifacts use `evidence_mode=real-component` or `live-provider` — never `fixture`.
4. Report `payment_provider=simulator` for V1 sandbox (live adapter later).
5. Absent/malformed/unauthorized peers surface as FAIL; no silent fixture substitution.
