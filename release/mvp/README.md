# SN-019 — MVP release-evidence verification kit

**State:** implemented verification kit with local positive/negative manifests.
Completing this module does **not** claim a shipped product or assembled MVP.

**Owned root:** `release/mvp/`
**Branch:** `feat/sn-019-mvp-acceptance`
**Produces:** `release-evidence.v1`
**Consumes (local stubs):** `core-assembly.v1`, `evaluation.v1`, `replay.v1`, `telemetry.v1`

Contract baseline: `sentinel.task-contracts.v1` · SHA-256
`0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.

## What this kit does

- Validates evidence manifests (component commit, contract hash, check
  command/result, artifact digest, observed mode, timestamp).
- Requires separate labels for `component_under_test`, `payment_provider`, and
  `model`.
- Blocks a **release verdict** when evidence is missing, failed, incompatible,
  or fixture-only under `--strict-release`.
- Runs standalone self-tests with **no product peers installed**; self-test
  `PASS` never sets `release_approved`.
- Documents clean-checkout/demo procedure steps via `procedure`.
- Renders a release report from a verified manifest.

## Setup

Requires Python 3.11+ and [uv](https://github.com/astral-sh/uv).

```sh
make -C release/mvp setup
```

Optional: copy `.env.example` and `peers.example.json` when exercising the
real-peer adapter against file/HTTP endpoints.

## Check

```sh
make -C release/mvp check
```

Runs unit/contract tests plus `self-test` against local manifests under
`contracts/manifests/`. No sibling Sentinel services or databases are required.

## Preview / CLI

```sh
make -C release/mvp preview
PYTHONPATH=src:. python -m sentinel_release_mvp verify \
  --manifest contracts/manifests/positive-fixture-selftest.json --json
PYTHONPATH=src:. python -m sentinel_release_mvp verify \
  --manifest contracts/manifests/negative-fixture-only.json --strict-release --json
PYTHONPATH=src:. python -m sentinel_release_mvp report \
  --manifest contracts/manifests/positive-real.json \
  --strict-release --artifact-root contracts/artifacts
```

## Local doubles

| Port               | Location                     | Cases                                                       |
| ------------------ | ---------------------------- | ----------------------------------------------------------- |
| `core-assembly.v1` | `tests/stubs/core_assembly/` | valid, unavailable, malformed, unauthorized_or_out_of_scope |
| `evaluation.v1`    | `tests/stubs/evaluation/`    | same                                                        |
| `replay.v1`        | `tests/stubs/replay/`        | same                                                        |
| `telemetry.v1`     | `tests/stubs/telemetry/`     | same                                                        |

Real-peer adapter: `adapters/real_peer.py` loads configured file/HTTP RunReports.
Missing, malformed, or unauthorized peers fail with `PeerError`. There is no
silent fixture fallback.

## Evidence labels

| Dimension            | Local self-test                  | Strict release example                  |
| -------------------- | -------------------------------- | --------------------------------------- |
| Component under test | fixture manifests                | `real`                                  |
| Payment provider     | `simulator`                      | `simulator` (external sandbox separate) |
| Model                | `fake`                           | `fake` or `live` (labeled only)         |
| Release approved     | always `false` for kit self-test | `true` only when strict checks pass     |

## Assembly limits

Owner-run assembly selects real component versions and records exact checks.
Fixture peers cannot satisfy product release evidence. See
`contracts/COMPATIBILITY.md`.
