"""Secrets must not survive redaction into logs or fixtures."""

from __future__ import annotations

from pathlib import Path

from sentinel_voice.adapters.redaction import contains_secret, redact_secrets

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "sarvam"
ENV_EXAMPLE = Path(__file__).resolve().parents[2] / ".env.example"


def test_redact_api_key_and_bearer() -> None:
    raw = "api_key=sk-live-secret-value Authorization: Bearer voice-demo-token"
    cleaned = redact_secrets(raw)
    assert not contains_secret(cleaned)
    assert "sk-live-secret-value" not in cleaned
    assert "voice-demo-token" not in cleaned
    assert "[REDACTED]" in cleaned


def test_fixtures_contain_no_live_secrets() -> None:
    for path in FIXTURES.glob("*.json"):
        text = path.read_text(encoding="utf-8")
        assert "SARVAM_API_KEY" not in text
        assert "sk-" not in text.lower()
        assert "api_key=" not in text.lower()


def test_env_example_has_no_live_key_value() -> None:
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    assert "SARVAM_API_KEY" in text
    for line in text.splitlines():
        stripped = line.strip().lstrip("#").strip()
        if stripped.startswith("SARVAM_API_KEY="):
            assert stripped == "SARVAM_API_KEY="
