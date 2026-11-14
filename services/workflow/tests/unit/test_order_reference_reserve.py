"""Reserve path must send explicit order_reference; missing fails closed."""

from __future__ import annotations

from fastapi.testclient import TestClient

from sentinel_workflow.adapters.peers_http import HttpLedger
from sentinel_workflow.domain.types import Approval, RefundAction, ReservationRequest
from tests.helpers import build_test_app
from tests.stubs import StubLedger, StubVerifier


def _approve_and_resume(client, ledger: StubLedger, peers, *, job_prefix: str):
    start = client.post(
        "/v1/runs",
        headers={"Authorization": "Bearer case-api-token"},
        json={
            "case_id": "case-demo-42",
            "case_revision": 1,
            "job_key": f"{job_prefix}-start",
            "event": "START",
        },
    )
    assert start.status_code == 202
    action_id = peers["case_api"].results[-1].action_id
    assert action_id
    approval = Approval(
        approval_id=f"approval-{job_prefix}",
        action_digest=ledger.get_action(action_id).action_digest,
        case_revision=1,
        policy_version="demo-policy-v1",
        decision="APPROVE",
        reviewer_id="supervisor-demo",
        expires_at="2026-11-14T00:00:00Z",
    )
    ledger.attach_approval(action_id, approval)
    resume = client.post(
        "/v1/runs",
        headers={"Authorization": "Bearer case-api-token"},
        json={
            "case_id": "case-demo-42",
            "case_revision": 1,
            "job_key": f"{job_prefix}-resume",
            "event": "DECISION",
        },
    )
    assert resume.status_code == 202
    return peers


def test_reserve_sends_order_reference_from_case_input(session_factory):
    ledger = StubLedger()
    app, _service, peers = build_test_app(
        session_factory=session_factory,
        ledger=ledger,
        verifier=StubVerifier(assessment_status="WAITING"),
    )
    client = TestClient(app)
    _approve_and_resume(client, ledger, peers, job_prefix="order-ref-ok")
    assert ledger.reserve_calls >= 1
    assert ledger.last_reserve is not None
    assert ledger.last_reserve.order_reference == "DEMO-ORDER-42"


def test_missing_order_reference_escalates(session_factory):
    """Blank case_input.order_reference fails closed before/at reserve."""
    from sentinel_workflow.adapters.fixture_peers import FixtureCaseApi
    from sentinel_workflow.domain.types import CaseInput, CaseMessage

    class BlankOrderCaseApi(FixtureCaseApi):
        def get_input(self, case_id: str, revision: int) -> CaseInput:
            self._guard()
            return CaseInput(
                case_id=case_id,
                case_revision=revision,
                original_text="charged twice",
                language="en-IN",
                order_reference="",
                messages=[
                    CaseMessage(
                        message_id="msg-1",
                        text="charged twice",
                        language="en-IN",
                        author="CUSTOMER",
                        occurred_at="2026-11-13T10:00:00Z",
                    )
                ],
            )

    ledger = StubLedger()
    app, _service, peers = build_test_app(
        session_factory=session_factory,
        ledger=ledger,
        case_api=BlankOrderCaseApi(),
        verifier=StubVerifier(assessment_status="WAITING"),
    )
    client = TestClient(app)
    _approve_and_resume(client, ledger, peers, job_prefix="order-ref-missing")
    statuses = [(r.status, r.reason_code) for r in peers["case_api"].results]
    assert any(s == "ESCALATED" and c == "ORDER_REFERENCE_REQUIRED" for s, c in statuses)
    assert ledger.last_reserve is None


def test_http_reserve_json_includes_order_reference(monkeypatch):
    captured: dict = {}

    class FakeResponse:
        status_code = 201

        def json(self):
            return {
                "action_id": "action-1",
                "provider_ref": "refund-1",
                "payload": {
                    "action": "REQUEST_REFUND",
                    "case_id": "case-demo-42",
                    "case_revision": 1,
                    "transaction_ref": "TXN-B",
                    "amount_minor": 150000,
                    "currency": "INR",
                    "destination": "ORIGINAL_PAYMENT_ROUTE",
                    "evidence_ids": ["evidence-payment-b", "evidence-order"],
                    "policy_version": "demo-policy-v1",
                },
                "action_digest": "d" * 64,
                "status": "RESERVED",
            }

    def fake_request(method, url, headers=None, json=None, timeout=None):
        captured["json"] = json
        return FakeResponse()

    import httpx

    monkeypatch.setattr(httpx, "request", fake_request)
    payload = RefundAction(
        case_id="case-demo-42",
        case_revision=1,
        transaction_ref="TXN-B",
        amount_minor=150000,
        evidence_ids=["evidence-payment-b", "evidence-order"],
        policy_version="demo-policy-v1",
    )
    HttpLedger("http://ledger", "token").reserve(
        ReservationRequest(
            operation_key="op-1",
            payload=payload,
            action_digest="d" * 64,
            approval_id="approval-1",
            order_reference="DEMO-ORDER-42",
        )
    )
    assert captured["json"]["order_reference"] == "DEMO-ORDER-42"
    assert "order_reference" not in captured["json"]["payload"]
