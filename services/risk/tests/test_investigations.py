"""Investigation CRUD and dashboard (FLOW-10 entry)."""

from __future__ import annotations

from tests.conftest import auth


def _create(client, *, case_id: str = "case-demo-42", reason: str = "SUSPECTED_DUPLICATE"):
    return client.post(
        "/v1/risk/investigations",
        headers={**auth(), "Idempotency-Key": f"idem-{case_id}-{reason}"},
        json={"case_id": case_id, "reason_code": reason, "queue_ref": "FRAUD"},
    )


def test_create_list_get_investigation(client):
    created = _create(client)
    assert created.status_code == 201
    body = created.json()
    assert body["case_id"] == "case-demo-42"
    assert body["status"] == "OPEN"
    assert len(body["restriction_ids"]) == 1
    investigation_id = body["investigation_id"]

    listed = client.get("/v1/risk/investigations", headers=auth())
    assert listed.status_code == 200
    ids = [item["investigation_id"] for item in listed.json()["investigations"]]
    assert investigation_id in ids

    fetched = client.get(f"/v1/risk/investigations/{investigation_id}", headers=auth())
    assert fetched.status_code == 200
    assert fetched.json()["investigation_id"] == investigation_id


def test_dashboard_counts_open_and_blocks(client):
    _create(client)
    response = client.get("/v1/risk/dashboard", headers=auth())
    assert response.status_code == 200
    body = response.json()
    assert body["open_investigations"] >= 1
    assert body["active_restrictions"] >= 1
    assert body["blocked_actions"] >= 1


def test_idempotent_create(client):
    headers = {**auth(), "Idempotency-Key": "same-key"}
    payload = {"case_id": "case-demo-42", "reason_code": "SUSPECTED_DUPLICATE"}
    first = client.post("/v1/risk/investigations", headers=headers, json=payload)
    second = client.post("/v1/risk/investigations", headers=headers, json=payload)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["investigation_id"] == second.json()["investigation_id"]


def test_capabilities(client):
    response = client.get("/v1/capabilities")
    assert response.status_code == 200
    body = response.json()
    assert body["component"] == "risk"
    assert body["port"] == "risk.v1"
    assert body["financial_authority"] is False


def test_operator_cannot_create(client):
    response = client.post(
        "/v1/risk/investigations",
        headers=auth("operator-token"),
        json={"case_id": "case-demo-42", "reason_code": "SUSPECTED_DUPLICATE"},
    )
    assert response.status_code == 403
