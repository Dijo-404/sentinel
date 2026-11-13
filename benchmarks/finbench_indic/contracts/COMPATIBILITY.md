# finbench.v1 compatibility checklist

Pinned baseline: `sentinel.task-contracts.v1` /
`0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.

## Wire boundary

| Item | Value |
| --- | --- |
| Produced port | `finbench.v1` |
| Input | Dataset manifest + injected `CandidateRunner` (+ optional peers) |
| Output | `EvaluationReport` / `RunReport` with hashes, denominators, variance, hard safety |
| Consumed ports | `finharness-runtime.v1`, `indic-context.v1` |
| Transport | Library/CLI (not mandatory HTTP) |

## Compatible

- Grouped synthetic scenarios: translations/paraphrases stay in one split.
- Manifest `dataset_sha256` and per-split hashes match computed digests.
- Model scores labeled `fake` / `live` / `recorded` separately from `system` scores.
- Hard safety regression yields `overall_status=FAIL` even when model averages are high.
- Real-peer adapters raise on unavailable / malformed / unauthorized peers.

## Incompatible / blocked

- Cross-split leakage of a `group_id` (translation or paraphrase in another split).
- Silent fixture fallback when a configured real peer fails.
- Treating fixture/fake model scores as live-provider evidence.
- Live-model mode without explicit enable (must refuse, not fake success).

## Assembly boundary (owner-run, unverified here)

Selecting real runtime/context peers, live model credentials, and product release
gates remain separate owner decisions. Completing this kit does **not** claim a
shipped FinHarness product or production safety certification.
