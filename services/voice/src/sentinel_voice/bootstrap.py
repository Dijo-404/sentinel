"""Composition root: config, tokens, Sarvam adapters, app."""

from __future__ import annotations

import os
from pathlib import Path

from sentinel_voice.adapters.auth import TokenMap
from sentinel_voice.adapters.http import create_app
from sentinel_voice.adapters.retention import InMemoryRetentionStore
from sentinel_voice.adapters.sarvam_fixture import FixtureSarvamSpeech
from sentinel_voice.adapters.sarvam_live import LiveSarvamSpeech
from sentinel_voice.application.speak import SpeakVoice
from sentinel_voice.application.transcribe import TranscribeVoice
from sentinel_voice.contracts import VoiceProviderError
from sentinel_voice.domain import reason_codes as rc
from sentinel_voice.domain.retention import normalize_retention_mode

MODULE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PRINCIPALS = MODULE_ROOT / "contracts" / "principals.json"
DEFAULT_FIXTURES = MODULE_ROOT / "fixtures" / "sarvam"


def build_app(
    *,
    principals_path: Path | None = None,
    fixtures_path: Path | None = None,
    mode: str | None = None,
    retention_mode: str | None = None,
):
    resolved_mode = mode or os.environ.get("VOICE_MODE", "fixture")
    if resolved_mode not in {"fixture", "real-peers"}:
        raise VoiceProviderError(
            "INVALID_CONFIG",
            "VOICE_MODE must be fixture or real-peers",
            status_code=500,
        )

    path = principals_path or Path(os.environ.get("VOICE_PRINCIPALS_PATH", str(DEFAULT_PRINCIPALS)))
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    tokens = TokenMap.from_path(path)

    fixtures = fixtures_path or Path(os.environ.get("VOICE_FIXTURES_PATH", str(DEFAULT_FIXTURES)))
    if not fixtures.is_absolute():
        fixtures = (Path.cwd() / fixtures).resolve()

    retention = InMemoryRetentionStore(
        normalize_retention_mode(retention_mode or os.environ.get("VOICE_RETENTION_MODE", "none"))
    )

    if resolved_mode == "fixture":
        speech: FixtureSarvamSpeech | LiveSarvamSpeech = FixtureSarvamSpeech(fixtures)
    else:
        api_key = os.environ.get("SARVAM_API_KEY", "")
        if not api_key:
            raise VoiceProviderError(
                rc.PROVIDER_UNAVAILABLE,
                "real-peers mode requires SARVAM_API_KEY; refusing silent fixture fallback",
                status_code=503,
            )
        speech = LiveSarvamSpeech(
            api_key=api_key,
            stt_url=os.environ.get("SARVAM_STT_URL", "https://api.sarvam.ai/speech-to-text"),
            tts_url=os.environ.get("SARVAM_TTS_URL", "https://api.sarvam.ai/text-to-speech"),
            stt_model=os.environ.get("SARVAM_STT_MODEL", "saaras:v4"),
        )

    transcribe = TranscribeVoice(stt=speech, retention=retention)
    speak = SpeakVoice(tts=speech)
    return create_app(
        transcribe=transcribe,
        speak=speak,
        tokens=tokens,
        mode=resolved_mode,
    )
