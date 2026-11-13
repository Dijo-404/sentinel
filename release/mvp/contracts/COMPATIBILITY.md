# release-evidence.v1 compatibility checklist

Pinned baseline: `sentinel.task-contracts.v1` /
`0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa`.

## Wire boundary

| Item | Value |
| --- | --- |
| Produced port | `release-evidence.v1` |
| Input | `RunInput` |
| Output | `RunReport` + kit-local `ReleaseVerdict` |
| Consumed ports | `core-assembly.v1`, `evaluation.v1`, `replay.v1`, `telemetry.v1` |
| Transport | Library/CLI (not mandatory HTTP) |

## Compatible

- Matching `contract_version` and baseline SHA-256 on the evidence manifest.
- Component evidence with commit, check command/result, artifact digest, mode, timestamp.
- Separate labels: `component_under_test`, `payment_provider`, `model`.
- Real-peer adapters that raise on unavailable / malformed / unauthorized peers.

## Incompatible / blocked for release approval

- Missing required component evidence.
- Failed or UNVERIFIED component `check_result`.
- Baseline or per-component contract hash mismatch.
- `evidence_mode: fixture` or `observed_mode: fixture` under `--strict-release`.
- `component_under_test: fixture` under `--strict-release`.
- Silent fixture fallback when a configured real peer fails.

## Assembly boundary (owner-run, unverified here)

Selecting real component versions, running journeys against live peers, and
signing an MVP product release remain separate owner decisions. Completing this
kit does **not** claim a shipped product.
