# SN-020 — FinHarness SDK (`finharness-sdk.v1`)

Optional reusable protocols, version-pinned case manifests, and an injected client against local ports. No independent refund executor, case store, or second financial authority. SN-009 `action-ledger.v1` remains sole approval/reservation/ledger owner.

**Owned root:** `packages/finharness-sdk/` · **Branch:** `feat/sn-020-finharness-extraction`

Contract: `sentinel.task-contracts.v1`, SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.

## Standalone setup and check

Requires Python 3.11+, [uv](https://docs.astral.sh/uv/), and GNU Make. No PostgreSQL, Docker, sibling packages, or live peers.

```sh
cd packages/finharness-sdk
make setup
make check
```

Or from the repository root:

```sh
make -C packages/finharness-sdk check
make check
```

`uv sync --frozen` installs only this module. `make check` runs Ruff lint/format and pytest against local stubs under `tests/stubs/`. All peer traffic is fixture-labeled. Real-peer assembly is unverified here.

Preview the sample workflow (defaults keep routing off):

```sh
make preview
uv run --frozen sentinel-finharness sample --enabled --mode shadow
uv run --frozen sentinel-finharness sample --enabled --mode harness --financial-writes --with-approval
```

`.env.example` documents switches; the SDK does not auto-load environment files.

## Public surface

```python
from sentinel_finharness import (
    CaseManifest,
    FinHarnessClient,
    RuntimeConfig,
    run_sample_workflow,
)

config = RuntimeConfig()  # enabled=False, financial_writes=False, notifications=False
manifest = CaseManifest.from_mapping({...})  # pins workflow/policy/model/verifier versions
client = FinHarnessClient(
    config=config,
    manifest=manifest,
    evidence=...,
    policy=...,
    ledger=...,
    verifier=...,
    indic_context=...,
    tenant_id="sandbox",
)
```

Capability gates:

| Capability | Default | Gate |
|---|---|---|
| Routing (`shadow`/`harness`) | off | `enabled=True` and `execution_mode` in `{shadow,harness}` |
| Ledger proposal/reservation | off | routing + `financial_writes=True` + not `shadow` |
| Notifications | off | routing + `notifications=True` |
| Reservation without `approval_id` | refused | contract validation + explicit `CapabilityDenied` bypass helper |

The client validates request/response shapes locally, delegates to injected ports, and never mints provider refund IDs or edits ledger tables.

## Local peer doubles

Under `tests/stubs/` for each of `evidence.v1`, `policy.v1`, `action-ledger.v1`, `verifier.v1`, `indic-context.v1`:

- `valid`
- `unavailable`
- `malformed`
- `unauthorized_or_out_of_scope`

## Artifacts

- Typed snapshot: `src/sentinel_finharness/contracts.py`, `ports.py`, `config.py`, `manifest.py`, `client.py`
- Port contract: `contracts/finharness-sdk.v1.json`
- Pinned manifest example: `fixtures/case-manifest.json`

## Limits

- Fixture peers only; real-component, payment-simulator, live-model, and product-assembly evidence are separate owner runs.
- No case persistence or dispatcher adapter in this package.
- Compatibility checklist: pin `contract_version`, reject unavailable/malformed/unauthorized peers without fixture fallback, keep financial writes and notifications explicit, never bypass SN-009 approval/reservation.
