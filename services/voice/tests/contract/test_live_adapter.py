"""Real-peer adapter rejects outage/malformed peers; never silent fixture fallback."""

from __future__ import annotations

import json

import httpx
import pytest

from sentinel_voice.adapters.sarvam_live import LiveSarvamSpeech
from sentinel_voice.bootstrap import build_app
from sentinel_voice.contracts import VoiceProviderError
from sentinel_voice.domain import reason_codes as rc


class _Transport(httpx.BaseTransport):
    def __init__(self, handler) -> None:
        self._handler = handler

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        return self._handler(request)


def test_live_requires_api_key() -> None:
    with pytest.raises(VoiceProviderError) as exc:
        LiveSarvamSpeech(
            api_key="",
            stt_url="https://example.test/stt",
            tts_url="https://example.test/tts",
        )
    assert exc.value.code == rc.PROVIDER_UNAVAILABLE


def test_real_peers_bootstrap_refuses_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SARVAM_API_KEY", raising=False)
    with pytest.raises(VoiceProviderError) as exc:
        build_app(mode="real-peers")
    assert "fixture fallback" in exc.value.message


def test_live_outage_stays_visible() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "down"})

    client = httpx.Client(transport=_Transport(handler))
    speech = LiveSarvamSpeech(
        api_key="test-key-not-for-production",
        stt_url="https://example.test/stt",
        tts_url="https://example.test/tts",
        client=client,
    )
    with pytest.raises(VoiceProviderError) as exc:
        speech.transcribe(audio_uri="https://example.test/a.wav", language="en-IN")
    assert exc.value.code == rc.PROVIDER_UNAVAILABLE
    speech.close()


def test_live_malformed_json() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not-json{")

    client = httpx.Client(transport=_Transport(handler))
    speech = LiveSarvamSpeech(
        api_key="test-key-not-for-production",
        stt_url="https://example.test/stt",
        tts_url="https://example.test/tts",
        client=client,
    )
    with pytest.raises(VoiceProviderError) as exc:
        speech.transcribe(audio_uri="https://example.test/a.wav", language="ta-IN")
    assert exc.value.code == rc.MALFORMED_PROVIDER_OUTPUT
    speech.close()


def test_live_missing_transcript_field() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"something_else": True})

    client = httpx.Client(transport=_Transport(handler))
    speech = LiveSarvamSpeech(
        api_key="test-key-not-for-production",
        stt_url="https://example.test/stt",
        tts_url="https://example.test/tts",
        client=client,
    )
    with pytest.raises(VoiceProviderError) as exc:
        speech.transcribe(audio_uri="https://example.test/a.wav", language="ta-IN")
    assert exc.value.code == rc.MALFORMED_PROVIDER_OUTPUT
    # Ensure request did not leak into exception message as raw key.
    assert "test-key-not-for-production" not in str(exc.value)
    speech.close()


def test_live_success_extracts_transcript() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        assert body["language_code"] == "en-IN"
        assert "test-key-not-for-production" not in request.content.decode("utf-8")
        return httpx.Response(200, json={"transcript": "status please"})

    client = httpx.Client(transport=_Transport(handler))
    speech = LiveSarvamSpeech(
        api_key="test-key-not-for-production",
        stt_url="https://example.test/stt",
        tts_url="https://example.test/tts",
        client=client,
    )
    assert speech.transcribe(audio_uri="https://example.test/a.wav", language="en-IN") == (
        "status please"
    )
    speech.close()
