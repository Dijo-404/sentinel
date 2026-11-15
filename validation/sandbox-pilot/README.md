# SN-026 — Build an independent sandbox pilot validation kit

**State:** module-local `sandbox-validation.v1` kit implemented. Fixture self-check passes. External pilot execution remains separately authorized and is not claimed by kit PASS.

**Owned root:** `validation/sandbox-pilot/`
**Branch:** `feat/sn-026-sandbox-pilot`
**Lane:** B · **Phase:** 2 · **Priority:** P1 · **Optional for MVP:** yes

## Outcome

Configurable second-workflow, load/restart/restore/kill-switch/rollback drivers and report validation using module-local service fakes. Deliver the kit independently; running an external pilot is separately authorized and is not a task-completion prerequisite.

## Independence

No task-completion prerequisites. This module installs, runs local checks, and is reviewable with every other Sentinel task implementation absent. Uses explicit local port doubles rather than another developer's server or an unfinished sibling import.

## Ownership and interfaces

- `validation/sandbox-pilot/**`
- Produces: `sandbox-validation.v1`
- Consumes: `core-assembly.v1`, `finharness-runtime.v1`, `finbench.v1`, `harness-telemetry.v1`, `harness-replay.v1`

Contract input: [baseline](../../docs/independent-task-contracts.md) · `sentinel.task-contracts.v1` · SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.

### Required local peer doubles

Under `tests/stubs/` for each consumed port: `valid`, `unavailable`, `malformed`, `unauthorized_or_out_of_scope`.

## Setup and checks

```sh
make -C validation/sandbox-pilot setup
make -C validation/sandbox-pilot check
make -C validation/sandbox-pilot preview
```

- `check` — ruff, pytest, and `sentinel-sandbox-pilot check` (fixture peers only).
- `preview` — fixture-mode driver run; report `pilot_verdict=KIT_ONLY`, `external_pilot_claimed=false`.

Configuration example: [.env.example](.env.example). Never production payment credentials.

## Drivers

| Driver            | Fixture behavior                                                 |
| ----------------- | ---------------------------------------------------------------- |
| `second_workflow` | Non-refund status workflow reusing the same peer ports           |
| `load`            | Concurrent synthetic operations; zero identity loss              |
| `restart`         | Preserves `action_id` / `provider_ref`; continues reconciliation |
| `restore`         | Checkpoint restore keeps runtime pin; forced failure cannot PASS |
| `kill_switch`     | Blocks new financial writes; reconciliation continues            |
| `rollback`        | New cases route to rollback runtime; in-flight pin unchanged     |

## Real-peer mode

Strict mode probes configured HTTP `/v1/capabilities` endpoints. Missing, malformed, unauthorized, or fixture-labeled peers fail visibly. There is no silent fixture fallback. Real driver execution against live peers is owner-selected and remains unverified until exercised outside this module.

External pilot claim requires `SANDBOX_PILOT_EXTERNAL_AUTHORIZATION=true` (or `--external-authorization`) plus `--claim-external-pilot`. Absent authorization cannot produce a successful pilot verdict. Even with authorization, the kit marks pilot evidence `UNVERIFIED` — kit PASS is not external pilot success.

## Compatibility checklist

- [x] Typed contract snapshot at `contracts/sandbox-validation.v1.json`
- [x] Integer minor-unit money in fixtures (`150000` INR paise)
- [x] Identity preservation across restart/restore/rollback
- [x] Kill switch stops new writes only
- [x] Strict real-peers rejects fixture evidence and missing peers
- [x] `external_pilot_claimed` stays false for fixture kit PASS
- [ ] Owner-run real-component / external pilot evidence (separate authorization)

## Evidence limits

- Local doubles: `tests/stubs/` + in-process `ReferenceBundle`
- No sibling source import; no shared root lockfile; no module database required for fixture check
- Payment provider: none (synthetic identities only)
- Model: none
- Assembled / external pilot: unverified
