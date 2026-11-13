"""Transcribe consented audio/text into a source-preserving VoiceResult."""

from __future__ import annotations

from sentinel_voice.application.ports import RetentionStore, SpeechToTextPort
from sentinel_voice.contracts import (
    Principal,
    VoiceForbiddenError,
    VoiceRequest,
    VoiceResult,
)
from sentinel_voice.domain import reason_codes as rc
from sentinel_voice.domain.ambiguity import analyze_transcript
from sentinel_voice.domain.retention import require_consent


class TranscribeVoice:
    def __init__(
        self,
        *,
        stt: SpeechToTextPort,
        retention: RetentionStore,
    ) -> None:
        self._stt = stt
        self._retention = retention

    def __call__(
        self,
        principal: Principal,
        request: VoiceRequest,
        *,
        request_id: str,
    ) -> VoiceResult:
        if "voice" not in principal.roles:
            raise VoiceForbiddenError(rc.ROLE_DENIED, "Principal lacks voice role")
        require_consent(request.consent)

        if request.text is not None:
            original = request.text
        else:
            assert request.audio_uri is not None
            original = self._stt.transcribe(
                audio_uri=request.audio_uri,
                language=request.language,
            )

        # Preserve exact source characters; never normalize Unicode for authority.
        ambiguous, codes = analyze_transcript(original)
        self._retention.remember(
            original_text=original,
            language=request.language,
            request_id=request_id,
        )
        return VoiceResult(
            original_text=original,
            language=request.language,
            ambiguous=ambiguous,
            reason_codes=codes,
        )
