"""Narrow ports for speech providers and retention."""

from __future__ import annotations

from typing import Protocol

from sentinel_voice.contracts import RetentionMode, SpeakResult


class SpeechToTextPort(Protocol):
    def transcribe(self, *, audio_uri: str, language: str) -> str:
        """Return source transcript text or raise VoiceProviderError."""


class TextToSpeechPort(Protocol):
    def synthesize(self, *, text: str, language: str) -> SpeakResult:
        """Return labeled speech output or raise VoiceProviderError."""


class RetentionStore(Protocol):
    @property
    def mode(self) -> RetentionMode: ...

    def remember(self, *, original_text: str, language: str, request_id: str) -> None:
        """Optionally retain a transcript under the configured retention mode."""

    def stored(self) -> tuple[dict[str, str], ...]:
        """Test/inspection hook; empty when mode is none."""
