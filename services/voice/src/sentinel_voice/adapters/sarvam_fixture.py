"""Labeled local Sarvam STT/TTS fixtures. Never requires live credentials."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sentinel_voice.contracts import SpeakResult, VoiceProviderError
from sentinel_voice.domain import reason_codes as rc


class FixtureSarvamSpeech:
    """Deterministic STT/TTS backed by module-local JSON fixtures."""

    evidence_mode = "fixture"

    def __init__(self, fixtures_dir: Path) -> None:
        self._dir = fixtures_dir
        manifest_path = fixtures_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("evidence_mode") != "fixture":
            raise VoiceProviderError(
                "INVALID_CONFIG",
                "Sarvam fixture manifest must declare evidence_mode=fixture",
                status_code=500,
            )
        entries = manifest.get("entries")
        if not isinstance(entries, dict):
            raise VoiceProviderError(
                "INVALID_CONFIG",
                "Sarvam fixture manifest entries must be an object",
                status_code=500,
            )
        self._entries: dict[str, str] = {str(k): str(v) for k, v in entries.items()}

    def _load(self, audio_uri: str) -> dict[str, Any]:
        relative = self._entries.get(audio_uri)
        if relative is None:
            raise VoiceProviderError(
                rc.PROVIDER_UNAVAILABLE,
                "Unknown fixture audio_uri; use text fallback at the client",
                status_code=503,
            )
        path = self._dir / relative
        return json.loads(path.read_text(encoding="utf-8"))

    def transcribe(self, *, audio_uri: str, language: str) -> str:
        payload = self._load(audio_uri)
        fault = payload.get("fault")
        if fault == "outage":
            raise VoiceProviderError(
                rc.PROVIDER_UNAVAILABLE,
                payload.get("message", "Provider outage"),
                status_code=503,
            )
        if fault == "malformed":
            raise VoiceProviderError(
                rc.MALFORMED_PROVIDER_OUTPUT,
                "Fixture Sarvam payload is malformed",
                status_code=422,
            )
        transcript = payload.get("transcript")
        if not isinstance(transcript, str) or transcript == "":
            raise VoiceProviderError(
                rc.MALFORMED_PROVIDER_OUTPUT,
                "Fixture Sarvam transcript missing",
                status_code=422,
            )
        # Request language is authoritative for the wire response; fixture may echo.
        _ = language
        return transcript

    def synthesize(self, *, text: str, language: str) -> SpeakResult:
        if not text:
            raise VoiceProviderError(
                "INVALID_INPUT",
                "TTS text must be nonempty",
                status_code=422,
            )
        # Synthetic URI only; labeled fixture evidence, never live audio bytes in check.
        uri = f"fixture://tts/{language}/{abs(hash(text)) & 0xFFFFFFFF:x}.wav"
        return SpeakResult(
            audio_uri=uri,
            language=language,
            evidence_mode="fixture",
            reason_codes=(rc.FIXTURE_SPEECH, rc.NO_FINANCIAL_AUTHORITY),
        )
