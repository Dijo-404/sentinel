# SN-018 — Independent replay and candidate-comparison runner

**State:** implemented module. Fixture-mode comparison evidence only; not product or live-provider proof.

**Owned root:** `replay/core/`  
**Branch:** `feat/sn-018-replay`  
**Produces:** `replay.v1` · **Consumes:** `evaluation.v1`, `payment-provider.v1` (local stubs)  
**Contract:** `sentinel.task-contracts.v1` · SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`

## Outcome

Virtual-clock event replay with injected simulator, candidate, and scorer ports. Bundled conforming and defective timeout-retry examples carry versions and seeds. Live evaluator or simulator implementations are not required.

## Setup

```sh
cd replay/core
make setup          # uv sync --frozen
make check          # ruff + pytest
make preview        # compare bundled dup_refund_timeout_001
```

Requires Python ≥3.11 and `uv`. No database. No sibling Sentinel packages. No production payment credentials.

## Behavior

1. **Defective candidate** (`defective-retry-v0`) mints a new refund reference after timeout → fails side-effect/state assertions (two simulated writes).
2. **Conforming candidate** (`conforming-reconcile-v1`) queries the original stable reference → one simulated refund side effect and `VERIFIED_RESOLVED`.
3. Replay **blocks** production write/notification route prefixes; records `fixture` / seed / model mode; real adapter absence is explicit (`absent`). Fixture evidence is never product release proof.
4. `real-peers` mode without configured peer URLs fails closed (`PEER_UNAVAILABLE`); never silently falls back to fixtures.

## Local peer doubles

| Port                  | Location                        | Cases                                                       |
| --------------------- | ------------------------------- | ----------------------------------------------------------- |
| `evaluation.v1`       | `tests/stubs/evaluation/`       | valid, unavailable, malformed, unauthorized_or_out_of_scope |
| `payment-provider.v1` | `tests/stubs/payment_provider/` | valid, unavailable, malformed, unauthorized_or_out_of_scope |

Sandbox refunds use an in-process simulator (`sandbox://…`). Real adapters live in `adapters/real_peers.py` and raise when peers are missing.

## Configuration

See `.env.example`. Defaults: `SENTINEL_REPLAY_MODE=fixture`, seed `42`, `SENTINEL_REPLAY_MODEL_MODE=fake`.

## Evidence limits

| Claim                       | Status                       |
| --------------------------- | ---------------------------- |
| Standalone `make check`     | Required; local only         |
| Real evaluation peer        | Unverified until assembled   |
| Real payment simulator peer | Unverified until assembled   |
| Live model inference        | Not used (`fake`)            |
| Product / pilot release     | Out of scope for this module |

## Layout

```text
replay/core/
  src/sentinel_replay/   # domain, application, adapters, CLI
  contracts/             # replay.v1 snapshot + compatibility checklist
  tests/                 # acceptance, peers, contract shape
  tests/stubs/           # evaluation.v1 + payment-provider.v1 doubles
```
