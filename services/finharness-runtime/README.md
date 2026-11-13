# SN-022 — Independent shadow and sandbox harness runtime

**State:** Implemented standalone `finharness-runtime.v1` with local fixture peers. Real-peer assembly unverified.

**Owned root:** `services/finharness-runtime/`  
**Branch:** `feat/sn-022-harness-runtime`  
**Lane:** A · **Phase:** 2 · **Priority:** P1 · **Optional for MVP:** yes

## Outcome

Pinned-case FinHarness runtime with injected SDK-compatible/model/safety ports and local doubles. Supports read-only shadow comparison, restart-safe version pins, guarded sandbox routing, and unknown-action reconciliation without becoming a second ledger.

## Standalone setup

```sh
cd services/finharness-runtime
make setup          # uv sync --frozen
make check          # ruff + pytest
make preview        # fixture self-check CLI
```

Requires Python ≥3.11 and [uv](https://github.com/astral-sh/uv). No sibling Sentinel services, root lockfile, or PostgreSQL for the local check.

Contract baseline: `sentinel.task-contracts.v1` · SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.

## Behavior

| Mode | Writes | Notifications | Notes |
| --- | --- | --- | --- |
| `legacy` | n/a | n/a | Routing off; new cases not pinned |
| `shadow` | never | never | Read-only proposal comparison; no write adapter/credentials |
| `harness` | only if `financial_writes=true` | only if explicitly enabled | Sandbox-tenant gated; SN-009 remains authority |

- **Pinning:** `start_case` records `runtime_version` + workflow pin. Survives config switch and process restart (`JsonCaseStore`).
- **Rollout/rollback:** `rollout_percent` affects **new** cases only. In-flight pins stay.
- **Shadow:** Compares candidate vs baseline proposal. Probes prove refund write / notify / credential paths are denied. Cannot send a second refund.
- **Reconcile:** `reconcile_unknown` queries the **original** `provider_ref`. Kill switch does not stop reconciliation; never mints a new refund ID.

## Local peer doubles

Under `tests/stubs/` (valid / unavailable / malformed / unauthorized_or_out_of_scope):

- `finharness-sdk.v1`, `indic-context.v1`, `evidence.v1`, `policy.v1`, `action-ledger.v1`, `verifier.v1`

Real adapters in `adapters/real_peers.py` fail closed when base URLs are absent — no silent fixture fallback. See `contracts/COMPATIBILITY.md`.

## Layout

```text
src/sentinel_finharness_runtime/
  domain/          # config, pins, comparison rules
  application/     # FinHarnessRuntime use cases + ports
  adapters/        # store, shadow safety, fixture/real peers, composition
contracts/         # finharness-runtime.v1 snapshot + checklist
fixtures/          # case manifest + baseline proposal
tests/stubs/       # required local peer doubles
```

## Evidence limits

- Local `make check` uses fixture peers only (`evidence_mode: fixture`).
- Not product release evidence. Real-peer / simulator / live-model / assembly remain unverified.
- This module owns **no** financial tables; SN-009 `action-ledger.v1` is sole authority.
