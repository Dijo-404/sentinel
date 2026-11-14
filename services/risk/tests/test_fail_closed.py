"""Unauthorized scope and unavailable peers fail closed."""

from __future__ import annotations

import httpx
import pytest

from sentinel_risk.adapters.peers_fixture import FixtureCaseApi, FixtureWorkflow
from sentinel_risk.adapters.peers_http import HttpCaseApi, HttpWorkflow
from sentinel_risk.application.errors import (
    ConfigurationError,
    PeerMalformedError,
    PeerUnauthorizedError,
    PeerUnavailableError,
)
from sentinel_risk.bootstrap import Settings, build_app
from sentinel_risk.domain.types import CreateInvestigationRequest
from tests.conftest import RISK_OFFICER, auth


class _Transport(httpx.BaseTransport):
    def __init__(self, handler):
        self._handler = handler

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        return self._handler(request)


def test_out_of_scope_case_denied(client):
    response = client.post(
        "/v1/risk/investigations",
        headers=auth(),
        json={"case_id": "case-unknown", "reason_code": "SUSPECTED_DUPLICATE"},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_supervisor_role_rejected(client):
    response = client.post(
        "/v1/risk/investigations",
        headers=auth("supervisor-token"),
        json={"case_id": "case-demo-42", "reason_code": "SUSPECTED_DUPLICATE"},
    )
    assert response.status_code == 403


def test_case_api_unavailable_on_create(service):
    service._case_api = FixtureCaseApi(behavior="unavailable")  # noqa: SLF001
    with pytest.raises(PeerUnavailableError):
        service.create_investigation(
            RISK_OFFICER,
            CreateInvestigationRequest(
                case_id="case-demo-42",
                reason_code="SUSPECTED_DUPLICATE",
            ),
        )


def test_case_api_malformed(service):
    service._case_api = FixtureCaseApi(behavior="malformed")  # noqa: SLF001
    with pytest.raises(PeerMalformedError):
        service.create_investigation(
            RISK_OFFICER,
            CreateInvestigationRequest(
                case_id="case-demo-42",
                reason_code="SUSPECTED_DUPLICATE",
            ),
        )


def test_workflow_unavailable_on_clear(service, store):
    inv = service.create_investigation(
        RISK_OFFICER,
        CreateInvestigationRequest(case_id="case-demo-42", reason_code="X"),
    )
    service._workflow = FixtureWorkflow(behavior="unavailable")  # noqa: SLF001
    restriction_id = inv.restriction_ids[0]
    from sentinel_risk.domain.types import RestrictionDecisionRequest

    with pytest.raises(PeerUnavailableError):
        service.decide_restriction(
            RISK_OFFICER,
            restriction_id,
            RestrictionDecisionRequest(decision="CLEAR", reason="ok"),
        )


def test_real_peers_requires_urls():
    with pytest.raises(ConfigurationError):
        Settings.from_environ({"RISK_MODE": "real-peers", "RISK_TOKENS": ""})
        build_app(
            Settings(
                mode="real-peers",
                tokens="",
                case_api_base_url="",
                case_api_token="",
                workflow_base_url="",
                workflow_token="",
                database_url="",
                contract_version="sentinel.task-contracts.v1",
            )
        )


def test_real_peers_refuses_default_memory_store():
    settings = Settings(
        mode="real-peers",
        tokens="risk-token=risk-1|tenant-demo|risk_officer|subj|case-demo-42|FRAUD",
        case_api_base_url="http://127.0.0.1:9",
        case_api_token="t",
        workflow_base_url="http://127.0.0.1:9",
        workflow_token="t",
        database_url="",
        contract_version="sentinel.task-contracts.v1",
    )
    with pytest.raises(PeerUnavailableError):
        build_app(settings)


def test_http_case_api_unauthorized():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"code": "FORBIDDEN"})

    client = httpx.Client(transport=_Transport(handler))
    peer = HttpCaseApi("http://case", "tok", client=client)
    with pytest.raises(PeerUnauthorizedError):
        peer.get_case("case-demo-42", principal=RISK_OFFICER)


def test_http_workflow_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"code": "DOWN"})

    client = httpx.Client(transport=_Transport(handler))
    peer = HttpWorkflow("http://workflow", "tok", client=client)
    from sentinel_risk.domain.types import ResumeEvent

    with pytest.raises(PeerUnavailableError):
        peer.emit_resume(
            ResumeEvent(
                event_type="risk.restriction.cleared",
                investigation_id="inv-1",
                case_id="case-1",
                restriction_id="rst-1",
                tenant_id="tenant-demo",
            ),
            principal=RISK_OFFICER,
        )


def test_cross_tenant_list_empty(client):
    created = client.post(
        "/v1/risk/investigations",
        headers=auth(),
        json={"case_id": "case-demo-42", "reason_code": "SUSPECTED_DUPLICATE"},
    )
    assert created.status_code == 201
    listed = client.get("/v1/risk/investigations", headers=auth("risk-other-tenant"))
    assert listed.status_code == 200
    assert listed.json()["investigations"] == []
