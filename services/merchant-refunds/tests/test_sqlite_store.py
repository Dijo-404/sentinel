"""Durable sqlite store survives reopen; real-peers accepts DATABASE_URL."""

from __future__ import annotations

from pathlib import Path

from tests.stubs import StubCaseApi, StubEvidence, StubLedger, StubPolicy

from sentinel_merchant_refunds.adapters.sqlite_store import SqliteRequestStore
from sentinel_merchant_refunds.bootstrap import build_app
from sentinel_merchant_refunds.domain.types import MerchantRefundRequest


def test_sqlite_store_round_trip(tmp_path: Path):
    path = tmp_path / "refunds.db"
    store = SqliteRequestStore(path)
    request = MerchantRefundRequest(
        request_id="req-1",
        tenant_id="tenant-demo-1",
        merchant_ref="merchant-demo-1",
        case_id="case-demo-42",
        transaction_ref="TXN-B",
        amount_minor=150000,
        currency="INR",
        evidence_ids=["evidence-payment-b"],
        rationale="dup",
        status="DRAFT",
    )
    store.put(request)
    store.put_idempotency("tenant-demo-1", "idem-1", request)

    reopened = SqliteRequestStore(path)
    loaded = reopened.get("tenant-demo-1", "req-1")
    assert loaded is not None
    assert loaded.request_id == "req-1"
    assert reopened.get_by_idempotency("tenant-demo-1", "idem-1") is not None


def test_real_peers_accepts_database_url(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("MERCHANT_REFUNDS_DATABASE_URL", f"sqlite:///{tmp_path / 'r.db'}")
    evidence = StubEvidence()
    evidence.seed_demo()
    app = build_app(
        mode="real-peers",
        case_api=StubCaseApi(),
        evidence=evidence,
        policy=StubPolicy(),
        ledger=StubLedger(),
    )
    assert app is not None


def test_http_policy_posts_evidence_objects():
    import httpx

    from sentinel_merchant_refunds.adapters.http_peers import HttpPolicyClient
    from sentinel_merchant_refunds.domain.types import Principal

    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = request.content
        return httpx.Response(
            200,
            json={
                "outcome": "REQUIRE_APPROVAL",
                "reason_codes": ["SUPERVISOR_REQUIRED"],
                "policy_version": "demo-policy-v1",
                "action_digest": "abc",
            },
        )

    client = HttpPolicyClient("http://policy.test", token="t")
    client._client = httpx.Client(
        transport=httpx.MockTransport(handler), base_url="http://policy.test"
    )
    principal = Principal(
        principal_id="p",
        tenant_id="t1",
        merchant_ref="m1",
        roles=["merchant_staff"],
    )
    client.evaluate(
        principal,
        payload={"action": "REQUEST_REFUND"},
        evidence=[{"evidence_id": "e1", "case_id": "c1"}],
    )
    import json

    body = json.loads(seen["body"].decode("utf-8"))
    assert "evidence" in body
    assert "evidence_ids" not in body
    assert body["evidence"][0]["evidence_id"] == "e1"
