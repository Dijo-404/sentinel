"""Shared fixtures for voice.v1 tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sentinel_voice.adapters.auth import TokenMap
from sentinel_voice.adapters.http import create_app
from sentinel_voice.adapters.retention import InMemoryRetentionStore
from sentinel_voice.adapters.sarvam_fixture import FixtureSarvamSpeech
from sentinel_voice.application.speak import SpeakVoice
from sentinel_voice.application.transcribe import TranscribeVoice

MODULE_ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = MODULE_ROOT / "contracts"
FIXTURES = MODULE_ROOT / "fixtures" / "sarvam"


@pytest.fixture
def tokens() -> TokenMap:
    return TokenMap.from_path(CONTRACTS / "principals.json")


@pytest.fixture
def retention() -> InMemoryRetentionStore:
    return InMemoryRetentionStore(mode="none")


@pytest.fixture
def speech() -> FixtureSarvamSpeech:
    return FixtureSarvamSpeech(FIXTURES)


@pytest.fixture
def transcribe(speech: FixtureSarvamSpeech, retention: InMemoryRetentionStore) -> TranscribeVoice:
    return TranscribeVoice(stt=speech, retention=retention)


@pytest.fixture
def speak(speech: FixtureSarvamSpeech) -> SpeakVoice:
    return SpeakVoice(tts=speech)


@pytest.fixture
def client(transcribe: TranscribeVoice, speak: SpeakVoice, tokens: TokenMap) -> TestClient:
    app = create_app(transcribe=transcribe, speak=speak, tokens=tokens, mode="fixture")
    return TestClient(app)


@pytest.fixture
def voice_auth() -> dict[str, str]:
    return {"Authorization": "Bearer voice-demo-token"}
