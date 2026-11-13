"""Typed standalone voice.v1 HTTP client (no web-shell dependency)."""

from __future__ import annotations

from typing import Any

import httpx

from sentinel_voice.contracts import SpeakResult, VoiceProviderError, VoiceResult
from sentinel_voice.domain import reason_codes as rc


class VoiceClient:
    """Minimal authenticated client for /v1/transcribe and /v1/speak."""

    def __init__(
        self,
        base_url: str,
        *,
        token: str,
        client: httpx.Client | None = None,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._token = token
        self._client = client or httpx.Client(timeout=30.0)
        self._owns_client = client is None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> VoiceClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _headers(self, request_id: str | None = None) -> dict[str, str]:
        headers = {"Authorization": f"Bearer {self._token}", "Accept": "application/json"}
        if request_id:
            headers["X-Request-Id"] = request_id
        return headers

    def capabilities(self) -> dict[str, Any]:
        response = self._client.get(f"{self._base}/v1/capabilities")
        response.raise_for_status()
        return response.json()

    def transcribe(
        self,
        *,
        language: str,
        consent: bool,
        text: str | None = None,
        audio_uri: str | None = None,
        request_id: str | None = None,
    ) -> VoiceResult:
        body: dict[str, Any] = {"language": language, "consent": consent}
        if text is not None:
            body["text"] = text
        if audio_uri is not None:
            body["audio_uri"] = audio_uri
        response = self._client.post(
            f"{self._base}/v1/transcribe",
            headers=self._headers(request_id),
            json=body,
        )
        payload = response.json()
        if response.status_code != 200:
            raise VoiceProviderError(
                str(payload.get("code", rc.PROVIDER_UNAVAILABLE)),
                str(payload.get("message", "transcribe failed")),
                status_code=response.status_code,
            )
        return VoiceResult(
            original_text=str(payload["original_text"]),
            language=str(payload["language"]),
            ambiguous=bool(payload["ambiguous"]),
            reason_codes=tuple(payload.get("reason_codes") or ()),
        )

    def speak(
        self,
        *,
        language: str,
        text: str,
        consent: bool,
        request_id: str | None = None,
    ) -> SpeakResult:
        response = self._client.post(
            f"{self._base}/v1/speak",
            headers=self._headers(request_id),
            json={"language": language, "text": text, "consent": consent},
        )
        payload = response.json()
        if response.status_code != 200:
            raise VoiceProviderError(
                str(payload.get("code", rc.PROVIDER_UNAVAILABLE)),
                str(payload.get("message", "speak failed")),
                status_code=response.status_code,
            )
        mode = payload.get("evidence_mode", "fixture")
        if mode not in {"fixture", "live-provider"}:
            mode = "fixture"
        return SpeakResult(
            audio_uri=str(payload["audio_uri"]),
            language=str(payload["language"]),
            evidence_mode=mode,  # type: ignore[arg-type]
            reason_codes=tuple(payload.get("reason_codes") or ()),
        )
