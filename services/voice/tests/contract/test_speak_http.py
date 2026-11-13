"""HTTP contract for optional POST /v1/speak."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_speak_fixture(client: TestClient, voice_auth: dict[str, str]) -> None:
    response = client.post(
        "/v1/speak",
        headers=voice_auth,
        json={
            "language": "ta-IN",
            "text": "உங்கள் வழக்கு பதிவு செய்யப்பட்டது",
            "consent": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["evidence_mode"] == "fixture"
    assert body["audio_uri"].startswith("fixture://tts/")
    assert "NO_FINANCIAL_AUTHORITY" in body["reason_codes"]
    assert "FIXTURE_SPEECH" in body["reason_codes"]


def test_speak_requires_consent(client: TestClient, voice_auth: dict[str, str]) -> None:
    response = client.post(
        "/v1/speak",
        headers=voice_auth,
        json={"language": "en-IN", "text": "hello", "consent": False},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "CONSENT_REQUIRED"
