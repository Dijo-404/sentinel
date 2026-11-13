"""Consent and retention gates for transcripts and speech."""

from __future__ import annotations

from sentinel_voice.contracts import RetentionMode, VoiceConsentError, VoiceInputError
from sentinel_voice.domain import reason_codes as rc


def require_consent(consent: bool) -> None:
    if not consent:
        raise VoiceConsentError(
            rc.CONSENT_REQUIRED,
            "Explicit consent is required before speech or transcript handling",
        )


def assert_retention_allows_store(mode: RetentionMode) -> None:
    if mode == "none":
        raise VoiceInputError(
            rc.RETENTION_DENIED,
            "Retention mode 'none' forbids durable transcript storage",
        )


def normalize_retention_mode(raw: str) -> RetentionMode:
    if raw not in {"none", "ephemeral", "restricted"}:
        raise VoiceInputError(
            "INVALID_CONFIG",
            "VOICE_RETENTION_MODE must be none, ephemeral, or restricted",
        )
    return raw  # type: ignore[return-value]
