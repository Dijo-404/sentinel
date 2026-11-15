"""HTTP acceptance: collect/list, auth, fixture states, digest retention."""

from __future__ import annotations

from sentinel_evidence.domain.digest import sha256_hex
from sentinel_evidence.domain.types import CONTRACT_VERSION


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_collect_valid_duplicate_bundle(client):
    response = client.post(
        "/v1/evidence/collect",
        headers=_auth("workflow-token"),
        json={
            "case_id": "case-demo-42",
            "case_revision": 1,
            "order_reference": "DEMO-ORDER-42",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["contract_version"] == CONTRACT_VERSION
    assert body["case_id"] == "case-demo-42"
    codes = body["reconciliation_codes"]
    assert "DUPLICATE_PAYMENT" in codes
    assert "DISTINCT_TRANSACTION_REFS" in codes
    assert "MERCHANT_CONFIRMED_DUPLICATE" in codes
    assert "ORDER_UNDERFULFILLED" in codes
    statuses = {item["verification_status"] for item in body["evidence"]}
    assert statuses == {"VERIFIED"}
    kinds = {item["facts"]["kind"] for item in body["evidence"]}
    assert kinds >= {"PAYMENT", "ORDER", "REFUND"}
    for item in body["evidence"]:
        assert len(item["digest"]) == 64
    payments = [item for item in body["evidence"] if item["facts"]["kind"] == "PAYMENT"]
    assert payments
    assert all(item["facts"]["payment"]["merchant_ref"] == "merchant-demo-1" for item in payments)


def test_equal_amounts_alone_via_api(client):
    response = client.post(
        "/v1/evidence/collect",
        headers=_auth("workflow-token"),
        json={
            "case_id": "case-demo-42",
            "case_revision": 1,
            "order_reference": "DEMO-ORDER-42#equal",
        },
    )
    assert response.status_code == 200
    codes = response.json()["reconciliation_codes"]
    assert "EQUAL_AMOUNTS_INSUFFICIENT" in codes
    assert "DUPLICATE_PAYMENT" not in codes


def test_stale_fixture_unverified(client):
    response = client.post(
        "/v1/evidence/collect",
        headers=_auth("workflow-token"),
        json={
            "case_id": "case-demo-42",
            "case_revision": 1,
            "order_reference": "DEMO-ORDER-42#stale",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "STALE_PROVIDER_SNAPSHOT" in body["reconciliation_codes"]
    assert {item["verification_status"] for item in body["evidence"]} == {"UNVERIFIED"}


def test_conflicting_fixture(client):
    response = client.post(
        "/v1/evidence/collect",
        headers=_auth("workflow-token"),
        json={
            "case_id": "case-demo-42",
            "case_revision": 1,
            "order_reference": "DEMO-ORDER-42#conflict",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "CONFLICTING_PAYMENT_RECORD" in body["reconciliation_codes"]
    assert {item["verification_status"] for item in body["evidence"]} == {"CONFLICTING"}


def test_unavailable_provider(client):
    response = client.post(
        "/v1/evidence/collect",
        headers=_auth("workflow-token"),
        json={
            "case_id": "case-demo-42",
            "case_revision": 1,
            "order_reference": "DEMO-ORDER-42#unavailable",
        },
    )
    assert response.status_code == 503
    assert response.json()["code"] == "PEER_UNAVAILABLE"


def test_malformed_provider(client):
    response = client.post(
        "/v1/evidence/collect",
        headers=_auth("workflow-token"),
        json={
            "case_id": "case-demo-42",
            "case_revision": 1,
            "order_reference": "DEMO-ORDER-42#malformed",
        },
    )
    assert response.status_code == 502
    assert response.json()["code"] == "PEER_MALFORMED"


def test_unauthorized_provider(client):
    response = client.post(
        "/v1/evidence/collect",
        headers=_auth("workflow-token"),
        json={
            "case_id": "case-demo-42",
            "case_revision": 1,
            "order_reference": "DEMO-ORDER-42#unauthorized",
        },
    )
    assert response.status_code == 403
    assert response.json()["code"] == "PEER_UNAUTHORIZED"


def test_list_after_collect_and_role_gates(client):
    collect = client.post(
        "/v1/evidence/collect",
        headers=_auth("verifier-token"),
        json={
            "case_id": "case-demo-42",
            "case_revision": 1,
            "order_reference": "DEMO-ORDER-42",
        },
    )
    assert collect.status_code == 200
    listed = client.get(
        "/v1/cases/case-demo-42/evidence",
        headers=_auth("operator-token"),
    )
    assert listed.status_code == 200
    assert listed.json()["case_id"] == "case-demo-42"
    denied = client.get(
        "/v1/cases/case-demo-42/evidence",
        headers=_auth("customer-token"),
    )
    assert denied.status_code == 403
    missing_auth = client.post(
        "/v1/evidence/collect",
        json={
            "case_id": "case-demo-42",
            "case_revision": 1,
            "order_reference": "DEMO-ORDER-42",
        },
    )
    assert missing_auth.status_code == 403


def test_digest_matches_retained_payload(client):
    from sentinel_evidence.adapters.provider_stub import StubPaymentProvider
    from sentinel_evidence.domain.types import Principal

    snapshot = StubPaymentProvider().fetch_snapshot(
        order_reference="DEMO-ORDER-42",
        principal=Principal("x", "t", ("workflow",), ("subj-demo-1",), ("case-demo-42",)),
    )
    response = client.post(
        "/v1/evidence/collect",
        headers=_auth("workflow-token"),
        json={
            "case_id": "case-demo-42",
            "case_revision": 1,
            "order_reference": "DEMO-ORDER-42",
        },
    )
    body = response.json()
    order_item = next(i for i in body["evidence"] if i["facts"]["kind"] == "ORDER")
    assert order_item["digest"] == sha256_hex(snapshot.order_payload)


def test_capabilities_and_health(client):
    assert client.get("/healthz").json()["status"] == "ok"
    caps = client.get("/v1/capabilities").json()
    assert caps == {
        "contract_version": CONTRACT_VERSION,
        "component": "evidence",
        "mode": "fixture",
    }
