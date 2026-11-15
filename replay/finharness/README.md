# SN-025 — Independent FinHarness replay and promotion gate

**State:** implemented module. Fixture-mode comparison evidence only; not product or live-provider proof.

**Owned root:** `replay/finharness/`  
**Branch:** `feat/sn-025-harness-replay`  
**Produces:** `harness-replay.v1` · **Consumes:** `finharness-runtime.v1`, `finbench.v1`, `replay.v1` (local stubs)  
**Contract:** `sentinel.task-contracts.v1` · SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`

## Outcome

Counterfactual replay with pinned context/runtime runner, synthetic fault schedule, injected candidate/scorer ports, and a mandatory safety promotion gate. Unchanged write sequences replay from a local recording; changed write sequences execute only against the in-process sandbox simulator. Candidates cannot alter live financial controls, policies, or production code.

## Setup

```sh
cd replay/finharness
make setup          # uv sync --frozen
make check          # ruff + pytest
make preview        # compare bundled dup_refund_timeout_001
```

Requires Python ≥3.11 and `uv`. No database. No sibling Sentinel packages. No production payment credentials.

## Behavior

1. **Record** a conforming baseline against the sandbox simulator, then **replay** the recording — state/effect/write sequence match deterministically.
2. **Changed writes** (defective dual-refund after timeout) skip the recording and run on the simulator with the fixture fault schedule.
3. **Safety gate:** a candidate with higher quality but critical safety regression is `REJECT` (`CRITICAL_SAFETY_REGRESSION_BLOCKS_PROMOTION`).
4. **Live controls** stay immutable: policy/approval/auth/provider-mapping/production-path patches raise `LiveControlMutationBlocked`.
5. Production write/notification route prefixes are blocked. Fixture evidence is never product release proof.
6. `real-peers` mode without configured peer URLs fails closed (`PEER_UNAVAILABLE`); with URLs it probes `/healthz` + `/v1/capabilities`. Never silently falls back to fixtures.

## Local peer doubles

| Port                    | Location                          | Cases                                                       |
| ----------------------- | --------------------------------- | ----------------------------------------------------------- |
| `finharness-runtime.v1` | `tests/stubs/finharness_runtime/` | valid, unavailable, malformed, unauthorized_or_out_of_scope |
| `finbench.v1`           | `tests/stubs/finbench/`           | valid, unavailable, malformed, unauthorized_or_out_of_scope |
| `replay.v1`             | `tests/stubs/replay/`             | valid, unavailable, malformed, unauthorized_or_out_of_scope |

Sandbox refunds use an in-process simulator (`sandbox://…`). Real adapters live in `adapters/real_peers.py` and raise when peers are missing.

## Configuration

See `.env.example`. Defaults: `SENTINEL_HARNESS_REPLAY_MODE=fixture`, seed `42`, `SENTINEL_HARNESS_REPLAY_MODEL_MODE=fake`.

## Evidence limits

| Claim                        | Status                       |
| ---------------------------- | ---------------------------- |
| Standalone `make check`      | Required; local only         |
| Real finharness-runtime peer | Unverified until assembled   |
| Real finbench peer           | Unverified until assembled   |
| Real replay.v1 peer          | Unverified until assembled   |
| Live model inference         | Not used (`fake`)            |
| Product / pilot release      | Out of scope for this module |

## Layout

```text
replay/finharness/
  src/sentinel_harness_replay/   # domain, application, adapters, CLI
  contracts/                     # harness-replay.v1 snapshot + compatibility checklist
  tests/                         # acceptance, peers, contract shape
  tests/stubs/                   # runtime + finbench + replay doubles
```
