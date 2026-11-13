"""Amount/negation fixtures preserve source text and flag ambiguity."""

from __future__ import annotations

import json
from pathlib import Path

from sentinel_voice.adapters.retention import InMemoryRetentionStore
from sentinel_voice.adapters.sarvam_fixture import FixtureSarvamSpeech
from sentinel_voice.application.transcribe import TranscribeVoice
from sentinel_voice.contracts import Principal, VoiceRequest, parse_voice_request
from sentinel_voice.domain import reason_codes as rc
from sentinel_voice.domain.ambiguity import analyze_transcript

MODULE = Path(__file__).resolve().parents[2]
CONTRACTS = MODULE / "contracts"
FIXTURES = MODULE / "fixtures" / "sarvam"

PRINCIPAL = Principal(
    principal_id="svc-voice-demo",
    tenant_id="demo-tenant-a",
    roles=("voice",),
    subject_refs=("subject-demo-42",),
    case_ids=("case-demo-42",),
)


def test_tamil_text_preserves_original_and_flags() -> None:
    request = parse_voice_request(
        json.loads((CONTRACTS / "voice.v1.transcribe.text-ta.request.json").read_text())
    )
    expected = json.loads((CONTRACTS / "voice.v1.transcribe.text-ta.result.json").read_text())
    use_case = TranscribeVoice(
        stt=FixtureSarvamSpeech(FIXTURES),
        retention=InMemoryRetentionStore(mode="none"),
    )
    result = use_case(PRINCIPAL, request, request_id="req-ta-1")
    assert result.as_dict() == expected
    assert result.original_text == request.text
    assert "REQUEST_REFUND" not in result.reason_codes
    assert rc.NO_FINANCIAL_AUTHORITY in result.reason_codes


def test_english_audio_fixture_preserves_transcript() -> None:
    request = parse_voice_request(
        json.loads((CONTRACTS / "voice.v1.transcribe.audio-en.request.json").read_text())
    )
    expected = json.loads((CONTRACTS / "voice.v1.transcribe.audio-en.result.json").read_text())
    use_case = TranscribeVoice(
        stt=FixtureSarvamSpeech(FIXTURES),
        retention=InMemoryRetentionStore(mode="none"),
    )
    result = use_case(PRINCIPAL, request, request_id="req-en-1")
    assert result.as_dict() == expected


def test_code_mixed_amount_flags_ambiguity() -> None:
    text = "enna ₹1500 illa fifteen hundred ah? duplicate payment cancel pannunga"
    ambiguous, codes = analyze_transcript(text)
    assert ambiguous is True
    assert rc.AMBIGUOUS_AMOUNT in codes
    assert rc.AMBIGUOUS_NEGATION in codes
    assert rc.CODE_MIXED_AMOUNT in codes
    assert rc.NO_FINANCIAL_AUTHORITY in codes


def test_clear_status_not_financially_authorizing() -> None:
    ambiguous, codes = analyze_transcript("Please tell me the status of my case")
    assert ambiguous is False
    assert codes == (rc.NO_FINANCIAL_AUTHORITY,)


def test_voice_request_requires_xor_input() -> None:
    request = VoiceRequest(language="en-IN", consent=True, text="hello", audio_uri=None)
    assert request.input_kind == "text"
