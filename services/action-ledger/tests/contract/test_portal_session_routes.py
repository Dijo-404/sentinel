"""Session-authenticated supervisor approves; approval records the identity user_id."""

from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from tests.conftest import DEMO_DIGEST, DEMO_PAYLOAD, auth_header
from tests.stubs.evidence import EvidenceStub
from tests.stubs.policy import PolicyStub

from sentinel_action_ledger.adapters.auth_tokens import demo_principals
from sentinel_action_ledger.adapters.portal_session import (
    HttpPortalSessionResolver,
    PortalSessionPrincipalMap,
)
from sentinel_action_ledger.bootstrap import build_app

pytestmark = pytest.mark.postgres

TENANT_SCOPE = {"scope_key": "tenant:tenant-demo", "merchant_ref": None, "team_id": None}
SESSIONS = {
    "sess-supervisor": ("usr-sup-7", "supervisor", TENANT_SCOPE),
    "sess-operator": ("usr-op-3", "operator", TENANT_SCOPE),
    "sess-sup-merchant": (
        "usr-sup-m",
        "supervisor",
        {"scope_key": "tenant:tenant-demo|merchant:m-1", "merchant_ref": "m-1", "team_id": None},
    ),
    "sess-sup-team": (
        "usr-sup-t",
        "supervisor",
        {"scope_key": "tenant:tenant-demo|team:t-1", "merchant_ref": None, "team_id": "t-1"},
    ),
    "sess-sup-noscope": ("usr-sup-n", "supervisor", {"merchant_ref": None, "team_id": None}),
    "sess-sup-othertenant": (
        "usr-sup-o",
        "supervisor",
        {"scope_key": "tenant:tenant-other", "merchant_ref": None, "team_id": None},
    ),
}


def fake_identity(request: httpx.Request) -> httpx.Response:
    token = request.headers.get("authorization", "").removeprefix("Bearer ")
    if token not in SESSIONS:
        return httpx.Response(401, json={"code": "UNAUTHORIZED"})
    user_id, role, scope = SESSIONS[token]
    return httpx.Response(
        200,
        json={
            "user": {"user_id": user_id, "status": "active"},
            "active_assignment": {
                "tenant_id": "tenant-demo",
                "role_id": role,
                "status": "active",
                **scope,
            },
        },
    )


@pytest.fixture
def session_client(engine, clock, guard):
    client = httpx.Client(transport=httpx.MockTransport(fake_identity))
    auth = PortalSessionPrincipalMap(
        demo_principals(), HttpPortalSessionResolver("http://identity.test", client=client)
    )
    app = build_app(
        engine=engine,
        evidence=EvidenceStub(guard=guard),
        policy=PolicyStub(guard=guard),
        auth=auth,
        clock=clock,
        mode="fixture",
        lease_seconds=300,
        network=guard,
    )
    return TestClient(app)


def _propose(client) -> str:
    proposed = client.post(
        "/v1/actions/proposals",
        headers=auth_header("tok-workflow"),
        json={
            "operation_key": "portal-session-1",
            "payload": DEMO_PAYLOAD,
            "action_digest": DEMO_DIGEST,
        },
    )
    assert proposed.status_code == 201, proposed.text
    return proposed.json()["action_id"]


def _decision(client, action_id: str, token: str):
    return client.post(
        f"/v1/actions/{action_id}/decisions",
        headers=auth_header(token),
        json={
            "decision": "APPROVE",
            "action_digest": DEMO_DIGEST,
            "case_revision": DEMO_PAYLOAD["case_revision"],
            "policy_version": DEMO_PAYLOAD["policy_version"],
            "expires_at": "2026-11-13T13:00:00Z",
        },
    )


def test_session_supervisor_approves_and_approval_records_user_id(session_client, engine):
    action_id = _propose(session_client)
    read = session_client.get(f"/v1/actions/{action_id}", headers=auth_header("sess-supervisor"))
    assert read.status_code == 200, read.text

    decided = _decision(session_client, action_id, "sess-supervisor")
    assert decided.status_code == 200, decided.text
    assert decided.json()["reviewer_id"] == "usr-sup-7"

    with engine.connect() as connection:
        reviewer = connection.execute(
            text("SELECT reviewer_id FROM approvals WHERE action_id = :a"), {"a": action_id}
        ).scalar_one()
        actor = connection.execute(
            text(
                "SELECT actor_id FROM financial_audit"
                " WHERE action_id = :a AND event_type = 'DECISION'"
            ),
            {"a": action_id},
        ).scalar_one()
    assert reviewer == "usr-sup-7"
    assert actor == "usr-sup-7"


def test_session_operator_reads_but_cannot_decide(session_client, engine):
    action_id = _propose(session_client)
    read = session_client.get(f"/v1/actions/{action_id}", headers=auth_header("sess-operator"))
    assert read.status_code == 200, read.text

    denied = _decision(session_client, action_id, "sess-operator")
    assert denied.status_code == 403, denied.text
    with engine.connect() as connection:
        count = connection.execute(text("SELECT count(*) FROM approvals")).scalar_one()
    assert count == 0


@pytest.mark.parametrize(
    "token", ["sess-sup-merchant", "sess-sup-team", "sess-sup-noscope", "sess-sup-othertenant"]
)
def test_narrow_or_bad_scope_supervisor_cannot_decide(session_client, engine, token):
    action_id = _propose(session_client)
    denied = _decision(session_client, action_id, token)
    assert denied.status_code == 403, denied.text
    with engine.connect() as connection:
        count = connection.execute(text("SELECT count(*) FROM approvals")).scalar_one()
    assert count == 0


def test_unknown_session_is_401(session_client):
    action_id = _propose(session_client)
    response = _decision(session_client, action_id, "sess-unknown")
    assert response.status_code == 401
