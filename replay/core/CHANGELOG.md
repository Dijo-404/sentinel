# SN-018 changelog

## Unreleased

### Added — 13 November 2026

- Independent module ownership, architecture/interface guide, scoped agent rules and acceptance checklist.
- `replay.v1` virtual-clock runner with injected sandbox simulator, conforming/defective candidates, and deterministic scorer.
- Bundled `dup_refund_timeout_001` fixture (seed 42, versioned policy/workflow/model).
- Local `evaluation.v1` and `payment-provider.v1` stubs; real-peer adapters that fail closed when absent.
- Production write/notification route guard; mode recording (fixture/seed/model/adapter presence).
- `make setup` / `make check` / `make preview`; contract snapshot and compatibility checklist.

### Implementation status

- Fixture-mode standalone checks implemented. Real evaluator/simulator assembly unverified.
- No live refunds; sandbox simulator only. Fixture evidence is not product release proof.
