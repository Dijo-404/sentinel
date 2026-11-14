"""Unauthorized scope and unavailable/malformed peers fail closed."""

from __future__ import annotations

import httpx
import pytest

from sentinel_merchant_disputes.adapters.peers_fixture import FixtureCaseApi, FixtureEvidence
from sentinel_merchant_disputes.adapters.peers_http import HttpCaseApi, HttpEvidence
from sentinel_merchant_disputes.application.errors import (
    ConfigurationError,
    PeerMalformedError,
    PeerUnauthorizedError,
    PeerUnavailableError,
)
from sentinel_merchant_disputes.bootstrap import Settings, build_app
from sentinel_merchant_disputes.domain.types import CreateDisputeRequest, Principal
from tests.conftest import OPERATOR, auth

PRINCIPAL = Principal(
    "op-1",
    "tenant-demo",
    ("operator",),
    ("subj-demo-1",),
    ("case-demo-42",),
    ("merchant-demo",),
)


class _Transport(httpx.BaseTransport):
    def __init__(self, handler):
        self._handler = handler

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        return self._handler(request)


def test_unauthorized_merchant_scope(client):
    response = client.post(
        "/v1/disputes",
        headers=auth("other-merchant-token"),
        json={
            "case_id": "case-demo-42",
            "merchant_ref": "merchant-demo",
            "reason_code": "CHARGEBACK_DUPLICATE",
            "order_reference": "DEMO-ORDER-42",
        },
    )
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_customer_role_rejected(client):
    response = client.post(
        "/v1/disputes",
        headers=auth("customer-token"),
        json={
            "case_id": "case-demo-42",
            "merchant_ref": "merchant-demo",
            "reason_code": "CHARGEBACK_DUPLICATE",
            "order_reference": "DEMO-ORDER-42",
        },
    )
    assert response.status_code == 403


def test_case_api_unavailable_on_create(service):
    service._case_api = FixtureCaseApi(behavior="unavailable")  # noqa: SLF001
    with pytest.raises(PeerUnavailableError):
        service.create(
            OPERATOR,
            CreateDisputeRequest(
                case_id="case-demo-42",
                merchant_ref="merchant-demo",
                reason_code="CHARGEBACK_DUPLICATE",
                order_reference="DEMO-ORDER-42",
            ),
        )


def test_evidence_unavailable_on_collect(service):
    dispute = service.create(
        OPERATOR,
        CreateDisputeRequest(
            case_id="case-demo-42",
            merchant_ref="merchant-demo",
            reason_code="CHARGEBACK_DUPLICATE",
            order_reference="DEMO-ORDER-42",
            deadline_at="2026-11-20T12:30:00Z",
        ),
    )
    service._evidence = FixtureEvidence(behavior="unavailable")  # noqa: SLF001
    with pytest.raises(PeerUnavailableError):
        service.collect_packet(OPERATOR, dispute.dispute_id)


def test_real_peers_requires_config():
    with pytest.raises(ConfigurationError):
        build_app(
            Settings(
                mode="real-peers",
                tokens="t=p|tenant|operator|s|c|m",
                case_api_base_url="",
                case_api_token="",
                evidence_base_url="",
                evidence_token="",
                default_deadline_seconds=60,
                contract_version="sentinel.task-contracts.v1",
            )
        )


def test_real_peers_refuses_default_memory_store():
    with pytest.raises(PeerUnavailableError, match="durable store"):
        build_app(
            Settings(
                mode="real-peers",
                tokens="t=p|tenant|operator|s|c|m",
                case_api_base_url="http://127.0.0.1:9",
                case_api_token="tok",
                evidence_base_url="http://127.0.0.1:9",
                evidence_token="tok",
                default_deadline_seconds=60,
                contract_version="sentinel.task-contracts.v1",
                database_url="",
            )
        )


def test_http_case_api_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    peer = HttpCaseApi(
        "http://case.test",
        "tok",
        client=httpx.Client(transport=_Transport(handler)),
    )
    with pytest.raises(PeerUnavailableError):
        peer.get_case("case-demo-42", principal=PRINCIPAL)


def test_http_evidence_unauthorized():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"code": "FORBIDDEN"})

    peer = HttpEvidence(
        "http://evidence.test",
        "tok",
        client=httpx.Client(transport=_Transport(handler)),
    )
    with pytest.raises(PeerUnauthorizedError):
        peer.collect(
            case_id="case-demo-42",
            case_revision=1,
            order_reference="DEMO-ORDER-42",
            principal=PRINCIPAL,
        )


def test_http_evidence_malformed():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not-json")

    peer = HttpEvidence(
        "http://evidence.test",
        "tok",
        client=httpx.Client(transport=_Transport(handler)),
    )
    with pytest.raises(PeerMalformedError):
        peer.collect(
            case_id="case-demo-42",
            case_revision=1,
            order_reference="DEMO-ORDER-42",
            principal=PRINCIPAL,
        )


def test_http_valid_path_no_fixture_fallback():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "contract_version": "sentinel.task-contracts.v1",
                "case_id": "case-demo-42",
                "evidence": [
                    {
                        "evidence_id": "evidence-payment-b",
                        "case_id": "case-demo-42",
                        "source": "live-peer",
                        "subject_ref": "subj-demo-1",
                        "observed_at": "2026-11-13T12:00:00Z",
                        "expires_at": "2026-11-13T18:00:00Z",
                        "digest": "b" * 64,
                        "verification_status": "VERIFIED",
                        "facts": {"kind": "PAYMENT", "payment": {}},
                    }
                ],
                "reconciliation_codes": [],
            },
        )

    peer = HttpEvidence(
        "http://evidence.test",
        "tok",
        client=httpx.Client(transport=_Transport(handler)),
    )
    bundle = peer.collect(
        case_id="case-demo-42",
        case_revision=1,
        order_reference="DEMO-ORDER-42",
        principal=PRINCIPAL,
    )
    assert bundle.evidence[0].source == "live-peer"
