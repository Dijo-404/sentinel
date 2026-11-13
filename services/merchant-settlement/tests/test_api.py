"""HTTP contract for merchant-settlement.v1 (fixture mode labeled)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

MODULE_ROOT = Path(__file__).resolve().parents[1]


def test_health_ready_capabilities(client: TestClient):
    assert client.get("/healthz").json() == {"status": "ok"}
    ready = client.get("/readyz").json()
    assert ready == {"status": "ready", "mode": "fixture"}
    caps = client.get("/v1/capabilities").json()
    assert caps["contract_version"] == "sentinel.task-contracts.v1"
    assert caps["component"] == "merchant-settlement"
    assert caps["mode"] == "fixture"


def test_import_list_assign_close(client: TestClient, auth_header: dict, fixture_batch_dict: dict):
    created = client.post(
        "/v1/settlements/batches",
        headers=auth_header,
        json=fixture_batch_dict,
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["contract_version"] == "sentinel.task-contracts.v1"
    kinds = {f["kind"] for f in body["findings"]}
    assert "FEE_DIFF" in kinds
    assert "SHORT_SETTLE" in kinds
    assert "DUPLICATE_ROW" in kinds
    assert "MISSING_PAYMENT" in kinds
    assert "MISSING_SETTLEMENT" in kinds
    assert "UNMATCHED_ORDER" in kinds

    listed = client.get(
        "/v1/settlements/findings",
        headers=auth_header,
        params={"batch_id": fixture_batch_dict["batch_id"]},
    )
    assert listed.status_code == 200
    assert len(listed.json()["findings"]) == len(body["findings"])

    finding_id = body["findings"][0]["finding_id"]
    assigned = client.post(
        f"/v1/settlements/findings/{finding_id}/assign",
        headers=auth_header,
        json={"assignee": "op-demo"},
    )
    assert assigned.status_code == 200
    assert assigned.json()["status"] == "ASSIGNED"
    assert assigned.json()["assignee"] == "op-demo"

    closed = client.post(
        f"/v1/settlements/findings/{finding_id}/close",
        headers=auth_header,
    )
    assert closed.status_code == 200
    assert closed.json()["status"] == "CLOSED"

    batch = client.get(
        f"/v1/settlements/batches/{fixture_batch_dict['batch_id']}",
        headers=auth_header,
    )
    assert batch.status_code == 200
    assert batch.json()["batch_id"] == fixture_batch_dict["batch_id"]


def test_csv_import(client: TestClient, auth_header: dict):
    csv_text = (MODULE_ROOT / "fixtures" / "settlement_batch.csv").read_text(encoding="utf-8")
    response = client.post(
        "/v1/settlements/batches",
        headers=auth_header,
        json={
            "batch_id": "batch-csv-1",
            "tenant_id": "demo-tenant-a",
            "merchant_ref": "demo-merchant-1",
            "period_start": "2026-11-01T00:00:00Z",
            "period_end": "2026-11-30T23:59:59Z",
            "currency": "INR",
            "csv_text": csv_text,
        },
    )
    assert response.status_code == 201, response.text
    kinds = {f["kind"] for f in response.json()["findings"]}
    assert "FEE_DIFF" in kinds
    assert "MISSING_SETTLEMENT" in kinds


def test_idempotent_same_digest(client: TestClient, auth_header: dict, fixture_batch_dict: dict):
    first = client.post("/v1/settlements/batches", headers=auth_header, json=fixture_batch_dict)
    second = client.post("/v1/settlements/batches", headers=auth_header, json=fixture_batch_dict)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["batch"]["source_digest"] == second.json()["batch"]["source_digest"]


def test_conflict_on_digest_mismatch(
    client: TestClient, auth_header: dict, fixture_batch_dict: dict
):
    first = client.post("/v1/settlements/batches", headers=auth_header, json=fixture_batch_dict)
    assert first.status_code == 201
    altered = dict(fixture_batch_dict)
    altered["rows"] = list(fixture_batch_dict["rows"]) + [
        {
            "row_id": "row-extra",
            "transaction_ref": "TXN-EXTRA",
            "settled_minor": 1,
            "fee_minor": 0,
            "occurred_at": "2026-11-02T16:00:00Z",
        }
    ]
    altered["source_digest"] = "different"
    conflict = client.post("/v1/settlements/batches", headers=auth_header, json=altered)
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "IDEMPOTENCY_CONFLICT"


def test_tenant_scope_denied(client: TestClient, fixture_batch_dict: dict):
    response = client.post(
        "/v1/settlements/batches",
        headers={"Authorization": "Bearer other-tenant-token"},
        json=fixture_batch_dict,
    )
    assert response.status_code == 403


def test_customer_forbidden(client: TestClient, fixture_batch_dict: dict):
    response = client.post(
        "/v1/settlements/batches",
        headers={"Authorization": "Bearer customer-demo-token"},
        json=fixture_batch_dict,
    )
    assert response.status_code == 403


def test_unauthorized(client: TestClient, fixture_batch_dict: dict):
    response = client.post("/v1/settlements/batches", json=fixture_batch_dict)
    assert response.status_code == 401
