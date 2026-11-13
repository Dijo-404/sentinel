# SN-017 changelog

## Unreleased

### Added — 13 November 2026

- Standalone `voice.v1` FastAPI service with `/v1/transcribe` and optional `/v1/speak`.
- Domain ambiguity analysis for Tamil/English/code-mixed amount and negation utterances; always emits `NO_FINANCIAL_AUTHORITY`.
- Labeled local Sarvam STT/TTS fixtures, text fallback signaling on provider failure, consent + retention controls, secret redaction.
- Typed `VoiceClient`, in-process client example, contract snapshots, compatibility checklist.
- Module-local `uv` lockfile and `make check` (ruff + pytest). Live Sarvam remains opt-in via `VOICE_MODE=real-peers`.

### Implementation status

- Fixture-mode standalone checks implemented. Live Sarvam assembly and web-shell integration remain unverified owner runs.
