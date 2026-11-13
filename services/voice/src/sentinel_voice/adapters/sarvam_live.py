"""Opt-in live Sarvam adapter. Never silently falls back to fixtures."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from sentinel_voice.adapters.redaction import redact_secrets
from sentinel_voice.contracts import SpeakResult, VoiceProviderError
from sentinel_voice.domain import reason_codes as rc


class LiveSarvamSpeech:
    """Real-peer STT/TTS. Requires SARVAM_API_KEY; failures stay visible."""

    evidence_mode = "live-provider"

    def __init__(
        self,
        *,
        api_key: str,
        stt_url: str,
        tts_url: str,
        stt_model: str = "saaras:v4",
        client: httpx.Client | None = None,
    ) -> None:
        if not api_key:
            raise VoiceProviderError(
                rc.PROVIDER_UNAVAILABLE,
                "SARVAM_API_KEY required for real-peers mode",
                status_code=503,
            )
        self._api_key = api_key
        self._stt_url = stt_url
        self._tts_url = tts_url
        self._stt_model = stt_model
        self._client = client or httpx.Client(timeout=30.0)
        self._owns_client = client is None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def _headers(self) -> dict[str, str]:
        return {
            "api-subscription-key": self._api_key,
            "Accept": "application/json",
        }

    def transcribe(self, *, audio_uri: str, language: str) -> str:
        try:
            response = self._client.post(
                self._stt_url,
                headers=self._headers(),
                json={
                    "model": self._stt_model,
                    "language_code": language,
                    "audio_url": audio_uri,
                },
            )
        except httpx.HTTPError as exc:
            raise VoiceProviderError(
                rc.PROVIDER_UNAVAILABLE,
                redact_secrets(f"Sarvam STT transport error: {exc}"),
                status_code=503,
            ) from exc
        if response.status_code >= 500:
            raise VoiceProviderError(
                rc.PROVIDER_UNAVAILABLE,
                "Sarvam STT unavailable",
                status_code=503,
            )
        if response.status_code >= 400:
            raise VoiceProviderError(
                rc.PROVIDER_UNAVAILABLE,
                "Sarvam STT rejected the request",
                status_code=503,
            )
        try:
            payload: Any = response.json()
        except ValueError as exc:
            raise VoiceProviderError(
                rc.MALFORMED_PROVIDER_OUTPUT,
                "Sarvam STT returned non-JSON",
                status_code=422,
            ) from exc
        return self._extract_transcript(payload)

    def synthesize(self, *, text: str, language: str) -> SpeakResult:
        try:
            response = self._client.post(
                self._tts_url,
                headers=self._headers(),
                json={"text": text, "target_language_code": language},
            )
        except httpx.HTTPError as exc:
            raise VoiceProviderError(
                rc.PROVIDER_UNAVAILABLE,
                redact_secrets(f"Sarvam TTS transport error: {exc}"),
                status_code=503,
            ) from exc
        if response.status_code >= 400:
            raise VoiceProviderError(
                rc.PROVIDER_UNAVAILABLE,
                "Sarvam TTS unavailable or rejected",
                status_code=503,
            )
        try:
            payload: Mapping[str, Any] = response.json()
        except ValueError as exc:
            raise VoiceProviderError(
                rc.MALFORMED_PROVIDER_OUTPUT,
                "Sarvam TTS returned non-JSON",
                status_code=422,
            ) from exc
        audio_uri = payload.get("audio_url") or payload.get("audio_uri")
        if not isinstance(audio_uri, str) or not audio_uri:
            raise VoiceProviderError(
                rc.MALFORMED_PROVIDER_OUTPUT,
                "Sarvam TTS missing audio_url",
                status_code=422,
            )
        return SpeakResult(
            audio_uri=audio_uri,
            language=language,
            evidence_mode="live-provider",
            reason_codes=(rc.NO_FINANCIAL_AUTHORITY,),
        )

    @staticmethod
    def _extract_transcript(payload: Any) -> str:
        if not isinstance(payload, dict):
            raise VoiceProviderError(
                rc.MALFORMED_PROVIDER_OUTPUT,
                "Sarvam STT payload must be an object",
                status_code=422,
            )
        for key in ("transcript", "text", "transcription"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                return value
        raise VoiceProviderError(
            rc.MALFORMED_PROVIDER_OUTPUT,
            "Sarvam STT payload missing transcript",
            status_code=422,
        )
