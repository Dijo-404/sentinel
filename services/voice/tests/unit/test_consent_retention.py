"""Consent and retention controls."""

from __future__ import annotations

from pathlib import Path

import pytest

from sentinel_voice.adapters.retention import InMemoryRetentionStore
from sentinel_voice.adapters.sarvam_fixture import FixtureSarvamSpeech
from sentinel_voice.application.transcribe import TranscribeVoice
from sentinel_voice.contracts import Principal, VoiceConsentError, VoiceRequest
from sentinel_voice.domain.retention import assert_retention_allows_store, require_consent

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "sarvam"

PRINCIPAL = Principal(
    principal_id="svc-voice-demo",
    tenant_id="demo-tenant-a",
    roles=("voice",),
    subject_refs=("subject-demo-42",),
    case_ids=("case-demo-42",),
)


def test_require_consent_rejects_false() -> None:
    with pytest.raises(VoiceConsentError) as exc:
        require_consent(False)
    assert exc.value.code == "CONSENT_REQUIRED"


def test_retention_none_stores_nothing() -> None:
    store = InMemoryRetentionStore(mode="none")
    use_case = TranscribeVoice(stt=FixtureSarvamSpeech(FIXTURES), retention=store)
    use_case(
        PRINCIPAL,
        VoiceRequest(language="en-IN", consent=True, text="status please"),
        request_id="req-ret-1",
    )
    assert store.stored() == ()


def test_retention_ephemeral_keeps_row() -> None:
    store = InMemoryRetentionStore(mode="ephemeral")
    use_case = TranscribeVoice(stt=FixtureSarvamSpeech(FIXTURES), retention=store)
    use_case(
        PRINCIPAL,
        VoiceRequest(language="en-IN", consent=True, text="status please"),
        request_id="req-ret-2",
    )
    rows = store.stored()
    assert len(rows) == 1
    assert rows[0]["request_id"] == "req-ret-2"
    assert rows[0]["original_text"] == "status please"


def test_assert_retention_none_denies_store() -> None:
    with pytest.raises(Exception) as exc:
        assert_retention_allows_store("none")
    assert getattr(exc.value, "code", "") == "RETENTION_DENIED"
