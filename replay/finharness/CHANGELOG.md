# SN-025 changelog

## Unreleased

### Changed (finding #13)

- Real-peers mode now invokes configured peer `/healthz` and `/v1/capabilities`
  instead of reporting `REAL_PEER_NOT_EXERCISED`.
- Reachable real-peers labeled capabilities → `PEER_CAPABILITIES_OK` / `PASS`.
- Unreachable or malformed peers → `FAIL`; fixture-labeled peers stay `UNVERIFIED`.

### Added — 13 November 2026

- Independent module ownership, architecture/interface guide, scoped agent rules and acceptance checklist.
- `harness-replay.v1` counterfactual replay with recorded/simulation paths, synthetic fault schedule, and injected runner/scorer ports.
- Mandatory safety promotion gate: critical safety regression blocks promotion despite quality gains.
- Live-control immutability: candidates cannot change policy, approval, auth, provider mapping, or production code paths.
- Bundled `dup_refund_timeout_001` fixture (seed 42, versioned policy/workflow/model/runtime + fault schedule).
- Local `finharness-runtime.v1`, `finbench.v1`, and `replay.v1` stubs; real-peer adapters that fail closed when absent.
- Production write/notification route guard; mode recording (fixture/seed/model/adapter presence/live-controls).
- `make setup` / `make check` / `make preview`; contract snapshot and compatibility checklist.

### Implementation status

- Fixture-mode standalone checks implemented.
- Real-peers health/capabilities probes exercised when URLs configured (mocked in unit tests).
- Full counterfactual compare against live runtime/finbench/replay remains owner-assembled.
- No live refunds; sandbox simulator only. Fixture evidence is not product release proof.
