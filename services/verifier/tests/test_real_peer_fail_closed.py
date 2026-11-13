"""Real-peer adapters and stub modes fail closed; no fixture fallback."""

from __future__ import annotations

import pytest
from tests.stubs.case_api import StubCaseApi
from tests.stubs.evidence import StubEvidence
from tests.stubs.ledger import StubLedger
from tests.stubs.provider import StubProvider

from sentinel_verifier.adapters.http_peers import HttpLedgerClient, HttpProviderClient
from sentinel_verifier.bootstrap import build_app
from sentinel_verifier.domain.errors import PeerError, PeerUnavailableError


@pytest.mark.parametrize(
    "mode",
    ["unavailable", "malformed", "unauthorized_or_out_of_scope"],
)
def test_provider_stub_modes_surface(mode):
    provider = StubProvider(mode=mode)  # type: ignore[arg-type]
    with pytest.raises(PeerError) as exc:
        provider.get_refund("refund-demo-1")
    assert exc.value.http_status in {403, 502, 503}


@pytest.mark.parametrize(
    "mode",
    ["unavailable", "malformed", "unauthorized_or_out_of_scope"],
)
def test_ledger_stub_modes_surface(mode):
    ledger = StubLedger(mode=mode)  # type: ignore[arg-type]
    with pytest.raises(PeerError):
        ledger.get_action("action-demo-1")


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
def test_case_api_stub_modes_surface(mode):
    case_api = StubCaseApi(mode=mode)  # type: ignore[arg-type]
    with pytest.raises(PeerError):
        case_api.get_case("case-demo-42")


def test_fixture_mode_requires_injected_peers():
    with pytest.raises(PeerUnavailableError):
        build_app(mode="fixture", store=object())


def test_http_provider_does_not_swallow_errors():
    import httpx

    # Construct client against a closed local port; connection fails closed.
    client = HttpProviderClient("http://127.0.0.1:9", token="token-verifier-demo", timeout=0.2)
    with pytest.raises(httpx.HTTPError):
        client.get_refund("refund-demo-1")
    client.close()


def test_http_ledger_reports_status_errors(monkeypatch):
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

    monkeypatch.setattr("sentinel_verifier.adapters.http_peers.httpx.Client", FakeClient)
    client = HttpLedgerClient("http://example.invalid", token="token")
    with pytest.raises(PeerError) as exc:
        client.get_action("action-demo-1")
    assert exc.value.code == "PEER_UNAVAILABLE"
    client.close()
