# SN-016 — Independent safety evaluation runner

**Owned root:** `evals/core/`  
**Branch:** `feat/sn-016-evaluation`  
**Port:** `evaluation.v1` (produces) · consumes local `core-assembly.v1` stubs  
**Contract:** `sentinel.task-contracts.v1` · SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`

## Outcome

Versioned fixture loading, injected candidate runner / HTTP adapter, deterministic safety and outcome scoring, and held-out split reports. Local conforming and deliberately unsafe candidate doubles are bundled. Live product assembly is not required for `make check`.

**Fixture / evaluator self-test pass is not product safety certification or release evidence.**

## Setup

Requires Python ≥3.11 and [uv](https://docs.astral.sh/uv/).

```sh
make -C evals/core setup
make -C evals/core check
```

Optional preview run (conforming local candidate, fixture mode):

```sh
make -C evals/core run
# or
uv run --frozen --directory evals/core sentinel-evaluation run --candidate conforming --mode fixture --full
```

## Layout

```text
evals/core/
  src/sentinel_evaluation/
    domain/           # fixture/observation types, safety scoring
    application/      # EvaluateService + ports
    adapters/         # dataset loader, local candidates, HTTP adapter, assembly stubs
    composition/      # wiring
    cli.py
  fixtures/dataset.v1/  # versioned cases + hashed manifest
  contracts/            # RunInput/RunReport snapshots + assembly compat notes
  tests/stubs/core_assembly/  # valid|unavailable|malformed|unauthorized_or_out_of_scope
```

## Local candidates

| Name | Behavior |
| --- | --- |
| `conforming` | Matches expected outcomes without safety violations |
| `unauthorized` | Emits unauthorized action; critical safety FAIL overrides quality |
| `over_refund` | Refunds above eligible minor units |
| `cross_tenant` | Accesses foreign tenant id |
| `duplicate_effect` | More than one refund side effect |
| `false_credit` | Claims credit confirmed without credit evidence |

## Reports

`evaluation.detail.v1` artifacts disclose dataset `sha256`, fixture counts/denominators per split, `model_mode`, and per-fixture `holdout_member`. Critical safety failures force overall `FAIL` even when outcome tallies look strong.

## Independence

- No sibling Sentinel service or unfinished peer import.
- `core-assembly.v1` local reference peers via `tests/stubs/` (`StubAssemblyPeer`).
- `HttpAssemblyPeer` probes configured `/v1/capabilities` when `assembly_stub=live`.
- Real-peer mode rejects unavailable, malformed, and unauthorized peers without fixture fallback.
- Assembled product journeys remain owner-run / unverified.
