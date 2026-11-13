# SN-021 changelog

## Unreleased

### Added — 13 November 2026

- Independent module ownership, architecture/interface guide, scoped agent rules and acceptance checklist.
- `sentinel-indic-context` package implementing `indic-context.v1` (`POST /v1/proposals`).
- Fake Sarvam adapter (default) and opt-in live Sarvam chat-completions adapter with explicit `fake-inference` vs `provider-observation` reports (latency, token cost units, native-review limit).
- Source-preserving Tamil/Hindi/English normalization and structured proposal validation (malformed, hallucinated refs, prompt injection, unsupported actions).
- Module-local fixtures, Makefile `check`/`preview`, `.env.example`, contract snapshot.

### Implementation status

- Standalone `make check` is the component evidence path (fake mode).
- Live Sarvam credentials are optional; live calls never silently fall back to fixtures.
- FinHarness/voice/workflow assembly and real provider pilot observations remain out of scope for this component PR.
