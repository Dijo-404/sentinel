# SN-017 — Optional Tamil voice adapter

**State:** implemented. Local `make check` exercises `voice.v1` with labeled Sarvam fixtures and text fallback only. Live Sarvam is opt-in and never required.

**Owned root:** `services/voice/`
**Branch:** `feat/sn-017-voice`
**Produces:** `voice.v1`
**Consumes:** nothing

Contract baseline: `sentinel.task-contracts.v1` · SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.

## Outcome

Opt-in speech/transcript ports with a standalone typed client, local Sarvam response fixtures, and text intake when STT is unavailable. Voice never authorizes financial action: amount/negation/code-mixed fixtures preserve `original_text` and set `ambiguous` with reason codes including `NO_FINANCIAL_AUTHORITY`.

## Setup and check

Requires `uv` on PATH. No sibling Sentinel service, shared lockfile, PostgreSQL, browser bundle, or live `SARVAM_API_KEY`.

```sh
make -C services/voice check
```

Runs lockfile sync, ruff, then pytest (unit + HTTP/client/live-adapter negatives). Observed mode: `fixture`.

## Run locally

```sh
cp services/voice/.env.example services/voice/.env   # documentation only; no secrets
make -C services/voice preview
# listens on VOICE_HOST/VOICE_PORT (default 127.0.0.1:8017)

make -C services/voice client
# in-process fixture client example (no web app)
```

Synthetic bearer: `voice-demo-token` from `contracts/principals.json`.

## Routes

| Method | Path | Auth | Notes |
| --- | --- | --- | --- |
| GET | `/healthz` | none | liveness |
| GET | `/readyz` | none | labels `mode`; fixture readiness includes `fixture_label` |
| GET | `/v1/capabilities` | none | `contract_version`, `component=voice`, `mode`, `port=voice.v1` |
| POST | `/v1/transcribe` | voice bearer | `{language, audio_uri\|text, consent}` → `{original_text, language, ambiguous, reason_codes}` |
| POST | `/v1/speak` | voice bearer | optional TTS; fixture returns labeled `fixture://tts/...` URI |

Exactly one of `audio_uri` or `text`. `consent=false` → 403. Provider outage/malformed audio fixtures → 503/422 with `TEXT_FALLBACK_AVAILABLE` so callers switch to text.

## Layout

```text
services/voice/
  src/sentinel_voice/
    domain/            # ambiguity, consent/retention, reason codes
    application/       # TranscribeVoice, SpeakVoice + ports
    adapters/          # FastAPI, tokens, fixture/live Sarvam, redaction, retention
    client.py          # typed standalone client
    examples/          # in-process client example
    bootstrap.py
  contracts/           # principals, request/result snapshots, compatibility checklist
  fixtures/sarvam/     # labeled STT fixtures (evidence_mode=fixture)
  tests/unit|contract
```

## Modes

| Mode | How | Notes |
| --- | --- | --- |
| `fixture` (default) | local JSON under `fixtures/sarvam/` | used by `make check` |
| `real-peers` | `VOICE_MODE=real-peers` + `SARVAM_API_KEY` | refuses missing key; never silent fixture fallback |

## Evidence limits

- Standalone fixture check only. Live Sarvam / assembled web-shell slot unverified here.
- No production credentials, browser secret bundles, real-money authority, or ledger writes.
- Retention default `none` stores nothing; `ephemeral`/`restricted` are in-process only.
