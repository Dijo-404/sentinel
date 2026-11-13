"""Task-local typed snapshot of voice.v1 wire types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

CONTRACT_VERSION = "sentinel.task-contracts.v1"
CONTRACT_SHA256 = "0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa"
PORT = "voice.v1"
COMPONENT = "voice"

RetentionMode = Literal["none", "ephemeral", "restricted"]
ProviderMode = Literal["fixture", "real-peers"]


class VoiceInputError(ValueError):
    """Malformed voice request; safe for API 422 mapping."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class VoiceConsentError(PermissionError):
    """Missing or false consent; safe for API 403 mapping."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class VoiceForbiddenError(PermissionError):
    """Authenticated but out of role/scope; safe for API 403 mapping."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class VoiceProviderError(RuntimeError):
    """Provider outage or malformed output; safe for API 503/422 mapping."""

    def __init__(self, code: str, message: str, *, status_code: int = 503) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class Principal:
    principal_id: str
    tenant_id: str
    roles: tuple[str, ...]
    subject_refs: tuple[str, ...]
    case_ids: tuple[str, ...]


@dataclass(frozen=True)
class VoiceRequest:
    language: str
    consent: bool
    text: str | None = None
    audio_uri: str | None = None

    @property
    def input_kind(self) -> Literal["text", "audio"]:
        return "text" if self.text is not None else "audio"


@dataclass(frozen=True)
class VoiceResult:
    original_text: str
    language: str
    ambiguous: bool
    reason_codes: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "original_text": self.original_text,
            "language": self.language,
            "ambiguous": self.ambiguous,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class SpeakRequest:
    language: str
    text: str
    consent: bool


@dataclass(frozen=True)
class SpeakResult:
    audio_uri: str
    language: str
    evidence_mode: Literal["fixture", "live-provider"]
    reason_codes: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "audio_uri": self.audio_uri,
            "language": self.language,
            "evidence_mode": self.evidence_mode,
            "reason_codes": list(self.reason_codes),
        }


def _require_str(obj: dict[str, Any], key: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value:
        raise VoiceInputError("INVALID_INPUT", f"Field '{key}' must be a nonempty string")
    return value


def _reject_unknown(obj: dict[str, Any], allowed: frozenset[str], label: str) -> None:
    extra = set(obj) - allowed
    if extra:
        raise VoiceInputError(
            "INVALID_INPUT",
            f"{label} has undeclared fields: {', '.join(sorted(extra))}",
        )


def parse_principal(raw: dict[str, Any]) -> Principal:
    _reject_unknown(
        raw,
        frozenset({"principal_id", "tenant_id", "roles", "subject_refs", "case_ids"}),
        "Principal",
    )
    roles = raw.get("roles")
    subjects = raw.get("subject_refs")
    cases = raw.get("case_ids")
    if not isinstance(roles, list) or not all(isinstance(r, str) for r in roles):
        raise VoiceInputError("INVALID_INPUT", "roles must be a string array")
    if not isinstance(subjects, list) or not all(isinstance(s, str) for s in subjects):
        raise VoiceInputError("INVALID_INPUT", "subject_refs must be a string array")
    if not isinstance(cases, list) or not all(isinstance(c, str) for c in cases):
        raise VoiceInputError("INVALID_INPUT", "case_ids must be a string array")
    return Principal(
        principal_id=_require_str(raw, "principal_id"),
        tenant_id=_require_str(raw, "tenant_id"),
        roles=tuple(roles),
        subject_refs=tuple(subjects),
        case_ids=tuple(cases),
    )


def parse_voice_request(raw: dict[str, Any]) -> VoiceRequest:
    if not isinstance(raw, dict):
        raise VoiceInputError("INVALID_INPUT", "body must be an object")
    _reject_unknown(raw, frozenset({"language", "audio_uri", "text", "consent"}), "VoiceRequest")
    language = _require_str(raw, "language")
    consent = raw.get("consent")
    if not isinstance(consent, bool):
        raise VoiceInputError("INVALID_INPUT", "consent must be a boolean")
    has_text = "text" in raw and raw["text"] is not None
    has_audio = "audio_uri" in raw and raw["audio_uri"] is not None
    if has_text == has_audio:
        raise VoiceInputError(
            "INVALID_INPUT",
            "Exactly one of audio_uri or text is required",
        )
    text = None
    audio_uri = None
    if has_text:
        if not isinstance(raw["text"], str) or raw["text"] == "":
            raise VoiceInputError("INVALID_INPUT", "text must be a nonempty string")
        text = raw["text"]
    else:
        if not isinstance(raw["audio_uri"], str) or raw["audio_uri"] == "":
            raise VoiceInputError("INVALID_INPUT", "audio_uri must be a nonempty string")
        audio_uri = raw["audio_uri"]
    return VoiceRequest(language=language, consent=consent, text=text, audio_uri=audio_uri)


def parse_speak_request(raw: dict[str, Any]) -> SpeakRequest:
    if not isinstance(raw, dict):
        raise VoiceInputError("INVALID_INPUT", "body must be an object")
    _reject_unknown(raw, frozenset({"language", "text", "consent"}), "SpeakRequest")
    consent = raw.get("consent")
    if not isinstance(consent, bool):
        raise VoiceInputError("INVALID_INPUT", "consent must be a boolean")
    return SpeakRequest(
        language=_require_str(raw, "language"),
        text=_require_str(raw, "text"),
        consent=consent,
    )
