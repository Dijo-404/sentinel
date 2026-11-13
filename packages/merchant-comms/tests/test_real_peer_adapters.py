"""Real-peer HTTP adapters reject unavailable/malformed/unauthorized peers."""

from __future__ import annotations

import json

import httpx
import pytest

from sentinel_merchant_comms.adapters.case_api_http import CaseApiHttpClient
from sentinel_merchant_comms.adapters.indic_context_http import IndicContextHttpClient
from sentinel_merchant_comms.application.errors import (
    PeerMalformedError,
    PeerUnauthorizedError,
    PeerUnavailableError,
)
from sentinel_merchant_comms.domain.types import CONTRACT_VERSION, Principal

CASE_JSON = {
    "contract_version": CONTRACT_VERSION,
    "case_id": "case-demo-42",
    "revision": 2,
    "status": "WAITING_APPROVAL",
    "language": "en-IN",
    "intent": "DUPLICATE_PAYMENT",
    "evidence_ids": ["evidence-payment-b", "evidence-order"],
    "action_id": "action-demo-1",
}


@pytest.fixture
def principal() -> Principal:
    return Principal(
        principal_id="op-demo",
        tenant_id="tenant-demo",
        roles=["operator"],
        subject_refs=["subject-demo"],
        case_ids=["case-demo-42"],
    )


def _transport(handler):
    return httpx.MockTransport(handler)


def test_case_api_http_valid(principal) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/cases/case-demo-42"
        return httpx.Response(200, json=CASE_JSON)

    client = CaseApiHttpClient(
        base_url="http://case.test", token="t", transport=_transport(handler)
    )
    case = client.get_case("case-demo-42", principal)
    assert case.case_id == "case-demo-42"
    client.close()


def test_case_api_http_unauthorized(principal) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"code": "NOT_FOUND", "message": "x", "request_id": "r"})

    client = CaseApiHttpClient(
        base_url="http://case.test", token="t", transport=_transport(handler)
    )
    with pytest.raises(PeerUnauthorizedError):
        client.get_case("case-demo-42", principal)
    client.close()


def test_case_api_http_unavailable(principal) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            503,
            json={"code": "PEER_UNAVAILABLE", "message": "x", "request_id": "r"},
        )

    client = CaseApiHttpClient(
        base_url="http://case.test", token="t", transport=_transport(handler)
    )
    with pytest.raises(PeerUnavailableError):
        client.get_case("case-demo-42", principal)
    client.close()


def test_case_api_http_malformed(principal) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not-json", headers={"content-type": "text/plain"})

    client = CaseApiHttpClient(
        base_url="http://case.test", token="t", transport=_transport(handler)
    )
    with pytest.raises(PeerMalformedError):
        client.get_case("case-demo-42", principal)
    client.close()


def test_case_api_http_network_error(principal) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    client = CaseApiHttpClient(
        base_url="http://case.test", token="t", transport=_transport(handler)
    )
    with pytest.raises(PeerUnavailableError):
        client.get_case("case-demo-42", principal)
    client.close()


def test_indic_http_valid(principal) -> None:
    from sentinel_merchant_comms.domain.types import Case

    case = Case.model_validate(CASE_JSON)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/proposals"
        body = json.loads(request.content.decode())
        assert body["case"]["case_id"] == "case-demo-42"
        return httpx.Response(
            200,
            json={
                "outcome": "NEEDS_INPUT",
                "reason_codes": ["STATUS_DRAFT"],
                "original_text": "x",
                "language": "en-IN",
                "inference_report": {"evidence_mode": "provider-observation"},
            },
        )

    client = IndicContextHttpClient(
        base_url="http://indic.test", token="t", transport=_transport(handler)
    )
    result = client.draft_status(case=case, language="en", principal=principal)
    assert "case-demo-42" in result.body
    assert result.evidence_mode == "provider-observation"
    client.close()


def test_indic_http_unauthorized(principal) -> None:
    from sentinel_merchant_comms.domain.types import Case

    case = Case.model_validate(CASE_JSON)

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"code": "FORBIDDEN", "message": "x", "request_id": "r"})

    client = IndicContextHttpClient(
        base_url="http://indic.test", token="t", transport=_transport(handler)
    )
    with pytest.raises(PeerUnauthorizedError):
        client.draft_status(case=case, language="en", principal=principal)
    client.close()
