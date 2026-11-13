"""HTTP contract for POST /v1/transcribe."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

CONTRACTS = Path(__file__).resolve().parents[2] / "contracts"


def test_capabilities(client: TestClient) -> None:
    response = client.get("/v1/capabilities")
    assert response.status_code == 200
    body = response.json()
    assert body["contract_version"] == "sentinel.task-contracts.v1"
    assert body["component"] == "voice"
    assert body["mode"] == "fixture"
    assert body["port"] == "voice.v1"


def test_health_ready(client: TestClient) -> None:
    assert client.get("/healthz").status_code == 200
    ready = client.get("/readyz").json()
    assert ready["mode"] == "fixture"
    assert ready["fixture_label"] == "local-sarvam-fixtures"


def test_missing_auth(client: TestClient) -> None:
    response = client.post(
        "/v1/transcribe",
        json={"language": "en-IN", "text": "hello", "consent": True},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"


def test_consent_required(client: TestClient, voice_auth: dict[str, str]) -> None:
    response = client.post(
        "/v1/transcribe",
        headers=voice_auth,
        json={"language": "en-IN", "text": "hello", "consent": False},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "CONSENT_REQUIRED"


def test_operator_role_denied(client: TestClient) -> None:
    response = client.post(
        "/v1/transcribe",
        headers={"Authorization": "Bearer operator-demo-token"},
        json={"language": "en-IN", "text": "hello", "consent": True},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "ROLE_DENIED"


def test_text_tamil_contract(client: TestClient, voice_auth: dict[str, str]) -> None:
    request = json.loads(
        (CONTRACTS / "voice.v1.transcribe.text-ta.request.json").read_text(encoding="utf-8")
    )
    expected = json.loads(
        (CONTRACTS / "voice.v1.transcribe.text-ta.result.json").read_text(encoding="utf-8")
    )
    response = client.post("/v1/transcribe", headers=voice_auth, json=request)
    assert response.status_code == 200
    assert response.json() == expected


def test_audio_english_contract(client: TestClient, voice_auth: dict[str, str]) -> None:
    request = json.loads(
        (CONTRACTS / "voice.v1.transcribe.audio-en.request.json").read_text(encoding="utf-8")
    )
    expected = json.loads(
        (CONTRACTS / "voice.v1.transcribe.audio-en.result.json").read_text(encoding="utf-8")
    )
    response = client.post("/v1/transcribe", headers=voice_auth, json=request)
    assert response.status_code == 200
    assert response.json() == expected


def test_code_mixed_audio(client: TestClient, voice_auth: dict[str, str]) -> None:
    response = client.post(
        "/v1/transcribe",
        headers=voice_auth,
        json={
            "language": "ta-IN",
            "audio_uri": "fixture://audio/code-mixed-amount.wav",
            "consent": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ambiguous"] is True
    assert "CODE_MIXED_AMOUNT" in body["reason_codes"]
    assert "NO_FINANCIAL_AUTHORITY" in body["reason_codes"]
    assert "₹1500" in body["original_text"]


def test_provider_outage_offers_text_fallback(
    client: TestClient, voice_auth: dict[str, str]
) -> None:
    response = client.post(
        "/v1/transcribe",
        headers=voice_auth,
        json={
            "language": "en-IN",
            "audio_uri": "fixture://audio/outage",
            "consent": True,
        },
    )
    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "PROVIDER_UNAVAILABLE"
    assert "TEXT_FALLBACK_AVAILABLE" in body["reason_codes"]
    assert "NO_FINANCIAL_AUTHORITY" in body["reason_codes"]


def test_malformed_provider_output(client: TestClient, voice_auth: dict[str, str]) -> None:
    response = client.post(
        "/v1/transcribe",
        headers=voice_auth,
        json={
            "language": "en-IN",
            "audio_uri": "fixture://audio/malformed",
            "consent": True,
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == "MALFORMED_PROVIDER_OUTPUT"


def test_both_inputs_rejected(client: TestClient, voice_auth: dict[str, str]) -> None:
    response = client.post(
        "/v1/transcribe",
        headers=voice_auth,
        json={
            "language": "en-IN",
            "text": "hello",
            "audio_uri": "fixture://audio/clear-status.wav",
            "consent": True,
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_INPUT"


def test_response_has_no_secret_fields(client: TestClient, voice_auth: dict[str, str]) -> None:
    response = client.post(
        "/v1/transcribe",
        headers=voice_auth,
        json={"language": "en-IN", "text": "status please", "consent": True},
    )
    raw = response.text.lower()
    assert "api_key" not in raw
    assert "bearer" not in raw
    assert "sk-" not in raw
