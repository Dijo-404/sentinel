"""Standalone typed client against in-process fixture app."""

from __future__ import annotations

from fastapi.testclient import TestClient

from sentinel_voice.bootstrap import build_app
from sentinel_voice.client import VoiceClient


def test_client_transcribe_and_speak() -> None:
    app = build_app(mode="fixture")
    with TestClient(app) as http:
        client = VoiceClient("http://testserver", token="voice-demo-token", client=http)
        caps = client.capabilities()
        assert caps["port"] == "voice.v1"
        result = client.transcribe(
            language="en-IN",
            consent=True,
            audio_uri="fixture://audio/clear-status.wav",
        )
        assert result.original_text == "Please tell me the status of my case"
        assert result.ambiguous is False
        spoken = client.speak(
            language="en-IN",
            text="Case received",
            consent=True,
        )
        assert spoken.evidence_mode == "fixture"
        assert spoken.audio_uri.startswith("fixture://tts/")
