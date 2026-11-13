# harness-replay.v1 real-peer compatibility checklist

Contract baseline: `sentinel.task-contracts.v1`  
SHA-256: `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`

## Consumed peers

| Port | Local stub | Real adapter | Fixture run | Real-peers run |
| --- | --- | --- | --- | --- |
| `finharness-runtime.v1` | `tests/stubs/finharness_runtime/` | `RealRuntimeAdapter` | not required | fails closed when URL absent; never fixture-fallback |
| `finbench.v1` | `tests/stubs/finbench/` | `RealFinbenchAdapter` | not required | fails closed when URL absent; never fixture-fallback |
| `replay.v1` | `tests/stubs/replay/` | `RealReplayAdapter` | not required | fails closed when URL absent; never fixture-fallback |

## Compatibility rules

1. Real-peer mode with missing URLs returns `PEER_UNAVAILABLE` / FAIL — never silent fixture success.
2. Fixture-mode comparison evidence is labeled `evidence_mode: fixture` and is not product release evidence.
3. Production write and notification route prefixes are blocked inside the sandbox simulator guard.
4. Candidates cannot mutate live financial controls (`policy_version`, approval, auth roles, provider mapping, production code paths).
5. Critical safety regression blocks promotion even when quality scores improve.
6. Unchanged write sequences may use recorded replay; changed write sequences always execute against the sandbox simulator.
7. Seed, model mode (`fake|live|absent`), and adapter presence are recorded on every `RunReport.modes`.
8. Assembly must pin compatible runtime, finbench, and replay.v1 versions separately; this module does not import sibling packages.
