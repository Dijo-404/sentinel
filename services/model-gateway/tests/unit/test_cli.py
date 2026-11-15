"""serve refuses unsafe non-loopback binds before starting uvicorn."""

from __future__ import annotations

import pytest

from sentinel_model_gateway import cli
from tests.conftest import BASE_ENV


@pytest.fixture
def started(monkeypatch):
    calls = []
    monkeypatch.setattr(cli.uvicorn, "run", lambda app, **kw: calls.append(kw))
    for key in ("MODEL_GATEWAY_REPLY_TOKENS", "MODEL_GATEWAY_HOST", "MODEL_GATEWAY_PORT"):
        monkeypatch.delenv(key, raising=False)
    return calls


def _env(monkeypatch, **env):
    for key, value in {**BASE_ENV, **env}.items():
        monkeypatch.setenv(key, value)


def test_loopback_without_reply_tokens_starts(monkeypatch, started):
    _env(monkeypatch)
    assert cli.main(["serve", "--host", "127.0.0.1", "--port", "8040"]) == 0
    assert started == [{"host": "127.0.0.1", "port": 8040, "log_level": "info"}]


def test_non_loopback_without_reply_tokens_refused(monkeypatch, started, capsys):
    _env(monkeypatch)
    assert cli.main(["serve", "--host", "0.0.0.0"]) == 2
    assert "MODEL_GATEWAY_REPLY_TOKENS" in capsys.readouterr().err
    assert started == []


def test_non_loopback_with_demo_proposal_token_refused(monkeypatch, started):
    _env(monkeypatch, MODEL_GATEWAY_TOKENS="tok-workflow", MODEL_GATEWAY_REPLY_TOKENS="r-secret")
    assert cli.main(["serve", "--host", "0.0.0.0"]) == 2
    assert started == []


def test_non_loopback_with_reply_tokens_starts(monkeypatch, started):
    _env(monkeypatch, MODEL_GATEWAY_REPLY_TOKENS="r-secret")
    assert cli.main(["serve", "--host", "0.0.0.0"]) == 0
    assert len(started) == 1
