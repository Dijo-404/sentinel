"""Real HTTP peer adapters reject unavailable/malformed/unauthorized — no fixture fallback."""

from __future__ import annotations

from dataclasses import dataclass

import httpx
import pytest

from sentinel_workflow.adapters.peers_http import HttpCaseApi, HttpEvidence, HttpPolicy
from sentinel_workflow.application.errors import PeerError, PeerUnavailableError


@dataclass
class FakeResponse:
    status_code: int
    _json: dict

    def json(self):
        return self._json


def test_http_case_unauthorized(monkeypatch):
    def fake_request(method, url, headers=None, json=None, timeout=None):
        return FakeResponse(403, {"code": "UNAUTHORIZED"})

    monkeypatch.setattr(httpx, "request", fake_request)
    with pytest.raises(PeerError) as exc:
        HttpCaseApi("http://peer", "token").get_case("case-demo-42")
    assert exc.value.status_code == 403


def test_http_case_malformed(monkeypatch):
    def fake_request(method, url, headers=None, json=None, timeout=None):
        return FakeResponse(200, {"not": "a-case"})

    monkeypatch.setattr(httpx, "request", fake_request)
    with pytest.raises(PeerError) as exc:
        HttpCaseApi("http://peer", "token").get_case("case-demo-42")
    assert exc.value.code == "MALFORMED"


def test_http_evidence_unavailable(monkeypatch):
    def fake_request(method, url, headers=None, json=None, timeout=None):
        return FakeResponse(503, {"code": "DOWN"})

    monkeypatch.setattr(httpx, "request", fake_request)
    with pytest.raises(PeerUnavailableError):
        HttpEvidence("http://peer", "token").collect("case-demo-42", 1, "DEMO-ORDER-42")


def test_http_policy_malformed(monkeypatch):
    from sentinel_workflow.domain.types import PolicyRequest

    def fake_request(method, url, headers=None, json=None, timeout=None):
        return FakeResponse(200, {"outcome": "ALLOW"})

    monkeypatch.setattr(httpx, "request", fake_request)
    with pytest.raises(PeerError) as exc:
        HttpPolicy("http://peer", "token").evaluate(
            PolicyRequest(payload={"action": "ESCALATE"}, evidence=[])
        )
    assert exc.value.code == "MALFORMED"


def test_http_transport_error(monkeypatch):
    def fake_request(method, url, headers=None, json=None, timeout=None):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(httpx, "request", fake_request)
    with pytest.raises(PeerUnavailableError):
        HttpCaseApi("http://peer", "token").get_case("case-demo-42")


def test_http_missing_base_url():
    with pytest.raises(PeerUnavailableError):
        HttpCaseApi("", "token").get_case("x")
