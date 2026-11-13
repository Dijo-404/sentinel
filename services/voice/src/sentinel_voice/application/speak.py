"""Optional consented text-to-speech; never financial authority."""

from __future__ import annotations

from sentinel_voice.application.ports import TextToSpeechPort
from sentinel_voice.contracts import (
    Principal,
    SpeakRequest,
    SpeakResult,
    VoiceForbiddenError,
)
from sentinel_voice.domain import reason_codes as rc
from sentinel_voice.domain.retention import require_consent


class SpeakVoice:
    def __init__(self, *, tts: TextToSpeechPort) -> None:
        self._tts = tts

    def __call__(self, principal: Principal, request: SpeakRequest) -> SpeakResult:
        if "voice" not in principal.roles:
            raise VoiceForbiddenError(rc.ROLE_DENIED, "Principal lacks voice role")
        require_consent(request.consent)
        return self._tts.synthesize(text=request.text, language=request.language)
