"""Unavailable/malformed/unauthorized peers fail closed; no fixture fallback."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from tests.stubs.case_api import StubCaseApi
from tests.stubs.evidence import StubEvidence

from sentinel_merchant_inbox.adapters.http_peers import HttpCaseApiClient, HttpEvidenceClient
from sentinel_merchant_inbox.bootstrap import DEMO_PEER_TOKEN, build_app
from sentinel_merchant_inbox.domain.errors import PeerError, PeerUnavailableError


@pytest.mark.parametrize(
    "mode",
    ["unavailable", "malformed", "unauthorized_or_out_of_scope"],
)
def test_case_api_stub_modes_surface(mode):
    case_api = StubCaseApi(mode=mode)  # type: ignore[arg-type]
    with pytest.raises(PeerError) as exc:
        case_api.get_case("case-demo-42")
    assert exc.value.http_status in {403, 502, 503}


@pytest.mark.parametrize(
    "mode",
    ["unavailable", "malformed", "unauthorized_or_out_of_scope"],
)
def test_evidence_stub_modes_surface(mode):
    evidence = StubEvidence(mode=mode)  # type: ignore[arg-type]
    with pytest.raises(PeerError):
        evidence.get_case_evidence("case-demo-42")


@pytest.mark.parametrize(
    "mode",
    ["unavailable", "malformed", "unauthorized_or_out_of_scope"],
)
def test_escalate_surfaces_peer_failure(mode, merchant_auth):
    case_api = StubCaseApi(mode=mode)  # type: ignore[arg-type]
    case_api.seed("case-demo-42")
    evidence = StubEvidence(mode="valid")
    evidence.seed("case-demo-42")
    app = build_app(case_api=case_api, evidence=evidence, mode="fixture")
    client = TestClient(app)
    response = client.post(
        "/v1/exceptions/exc-paid-unfulfilled-1/escalate",
        json={"reason_code": "PEER_CHECK"},
        headers=merchant_auth,
    )
    assert response.status_code in {403, 502, 503}
    assert response.json()["code"] in {
        "PEER_UNAVAILABLE",
        "MALFORMED_PEER",
        "FORBIDDEN",
    }


def test_fixture_mode_requires_injected_peers():
    with pytest.raises(PeerUnavailableError):
        build_app(mode="fixture")


def test_real_peers_refuses_demo_token(monkeypatch):
    monkeypatch.setenv("MERCHANT_INBOX_PEER_TOKEN", DEMO_PEER_TOKEN)
    monkeypatch.setenv("CASE_API_BASE_URL", "http://127.0.0.1:9")
    monkeypatch.setenv("EVIDENCE_BASE_URL", "http://127.0.0.1:9")
    with pytest.raises(PeerUnavailableError, match="MERCHANT_INBOX_PEER_TOKEN"):
        build_app(mode="real-peers", store=object())


def test_real_peers_refuses_missing_urls(monkeypatch):
    monkeypatch.setenv("MERCHANT_INBOX_PEER_TOKEN", "non-demo-peer-token")
    monkeypatch.delenv("CASE_API_BASE_URL", raising=False)
    monkeypatch.delenv("EVIDENCE_BASE_URL", raising=False)
    with pytest.raises(KeyError):
        build_app(mode="real-peers", store=object())


def test_http_case_api_does_not_swallow_errors():
    import httpx

    client = HttpCaseApiClient("http://127.0.0.1:9", token="token", timeout=0.2)
    with pytest.raises(httpx.HTTPError):
        client.get_case("case-demo-42")
    client.close()


def test_http_evidence_reports_status_errors(monkeypatch):
    class FakeResponse:
        status_code = 503
        text = "down"

        def json(self):
            return {"code": "PEER_UNAVAILABLE", "message": "Required peer unavailable"}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            del args, kwargs

        def get(self, path):
            del path
            return FakeResponse()

        def close(self):
            return None

    monkeypatch.setattr("sentinel_merchant_inbox.adapters.http_peers.httpx.Client", FakeClient)
    client = HttpEvidenceClient("http://example.invalid", token="token")
    with pytest.raises(PeerError) as exc:
        client.get_case_evidence("case-demo-42")
    assert exc.value.code == "PEER_UNAVAILABLE"
    client.close()
