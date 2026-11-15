# SN-023 — FinBench-Indic dataset and CLI

**Owned root:** `benchmarks/finbench_indic/`  
**Branch:** `feat/sn-023-finbench`  
**Produces:** `finbench.v1`  
**Consumes (local stubs / optional real adapters):** `finharness-runtime.v1`, `indic-context.v1`  
**Contract baseline:** `sentinel.task-contracts.v1` / `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`

## Outcome

Grouped synthetic Indic financial scenarios with version/hash manifests, deterministic scoring, and injected candidate adapters (recorded / fake / opt-in live / unsafe fault demo). Standalone CLI and tests do not require live context or runtime peers.

## Setup

```sh
cd benchmarks/finbench_indic
uv sync --frozen
```

Optional: copy `.env.example` for documentation. Fixture checks need no secrets.

## Check

```sh
make -C benchmarks/finbench_indic check
```

Runs ruff + pytest using only this module, bundled synthetic datasets, and `tests/stubs/`.

## Preview

```sh
uv run --frozen sentinel-finbench run --dataset indic-fin-v0.1.0 --split val --mode recorded
uv run --frozen sentinel-finbench self-test
```

Modes: `recorded`, `fake-model`, `live-model` (requires `--live-model` and `--context-peer`), `system`, `unsafe` (fault demo). Optional `--runtime-peer` discloses FinHarness runtime probe under report peers.

Probe real peers (fail closed; no fixture fallback):

```sh
uv run --frozen sentinel-finbench probe-peers \
  --runtime-peer tests/stubs/finharness_runtime/valid.json \
  --context-peer tests/stubs/indic_context/valid.json
```

## Acceptance behavior

1. Translations/paraphrases of one `group_id` stay in one split; reports disclose dataset/split hashes, denominators, and variance.
2. Hard safety regressions fail the run even when model averages look strong; `fake` / `live` / `recorded` model scores stay separate from deterministic `system` scores.
3. `make check` passes with sibling implementations absent.

## Layout

| Path                         | Role                                             |
| ---------------------------- | ------------------------------------------------ |
| `datasets/indic-fin-v0.1.0/` | Synthetic grouped scenarios + hashed manifest    |
| `src/sentinel_finbench/`     | Domain rules, evaluation use case, adapters, CLI |
| `contracts/`                 | `finbench.v1` snapshot + compatibility checklist |
| `tests/stubs/`               | finharness-runtime + indic-context doubles       |

## Evidence limits

- Fixture / recorded / fake only. Real-peer assembly, payment simulator, and live-provider evidence remain **unverified** here.
- Synthetic utterances are not native-speaker certified language quality claims.
- No financial tables, refund executor, or production credentials in this module.
