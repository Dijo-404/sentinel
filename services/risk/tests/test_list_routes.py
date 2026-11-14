"""Portal list GETs: queue/holds/transactions/audit via investigations/restrictions/findings."""

from __future__ import annotations

from tests.conftest import auth


def _seed_open_case(client):
    created = client.post(
        "/v1/risk/investigations",
        headers={**auth(), "Idempotency-Key": "list-routes-demo"},
        json={
            "case_id": "case-demo-42",
            "reason_code": "SUSPECTED_DUPLICATE",
            "queue_ref": "FRAUD",
            "severity": "HIGH",
            "evidence_ids": ["evidence-payment-b"],
        },
    )
    assert created.status_code == 201
    investigation = created.json()
    finding = client.post(
        f"/v1/risk/investigations/{investigation['investigation_id']}/findings",
        headers=auth(),
        json={
            "classification": "SUSPICIOUS",
            "evidence_ids": ["evidence-payment-b"],
            "notes": "sandbox audit finding",
            "expected_revision": investigation["revision"],
        },
    )
    assert finding.status_code == 201
    return investigation, finding.json()


def test_queue_lists_investigations(client):
    investigation, _ = _seed_open_case(client)
    response = client.get("/v1/risk/investigations", headers=auth())
    assert response.status_code == 200
    ids = [item["investigation_id"] for item in response.json()["investigations"]]
    assert investigation["investigation_id"] in ids


def test_holds_list_active_restrictions(client):
    investigation, _ = _seed_open_case(client)
    response = client.get(
        "/v1/risk/restrictions",
        headers=auth(),
        params={"blocks_financial_actions": "true"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "restrictions" in body
    assert len(body["restrictions"]) >= 1
    rst = body["restrictions"][0]
    assert rst["case_id"] == "case-demo-42"
    assert rst["blocks_financial_actions"] is True
    assert rst["investigation_id"] == investigation["investigation_id"]
    assert rst["financial_approval_granted"] is False


def test_transactions_list_filters_transaction_ref(client, store):
    # Memory path: attach transaction_ref on the active restriction after create.
    investigation, _ = _seed_open_case(client)
    restriction_id = investigation["restriction_ids"][0]
    current = store.get_restriction(restriction_id)
    assert current is not None
    from dataclasses import replace

    store.save_restriction(replace(current, transaction_ref="TXN-B", revision=current.revision))
    response = client.get(
        "/v1/risk/restrictions",
        headers=auth(),
        params={"has_transaction_ref": "true"},
    )
    assert response.status_code == 200
    refs = [item["transaction_ref"] for item in response.json()["restrictions"]]
    assert "TXN-B" in refs


def test_audit_lists_findings(client):
    investigation, finding = _seed_open_case(client)
    response = client.get("/v1/risk/findings", headers=auth())
    assert response.status_code == 200
    body = response.json()
    assert "findings" in body
    ids = [item["finding_id"] for item in body["findings"]]
    assert finding["finding_id"] in ids
    scoped = client.get(
        "/v1/risk/findings",
        headers=auth(),
        params={"investigation_id": investigation["investigation_id"]},
    )
    assert scoped.status_code == 200
    assert len(scoped.json()["findings"]) >= 1


def test_analytics_and_reports_use_dashboard(client):
    _seed_open_case(client)
    dashboard = client.get("/v1/risk/dashboard", headers=auth())
    reports = client.get("/v1/risk/reports", headers=auth())
    assert dashboard.status_code == 200
    assert reports.status_code == 200
    assert reports.json()["open_investigations"] == dashboard.json()["open_investigations"]
    assert reports.json()["active_restrictions"] == dashboard.json()["active_restrictions"]
    assert "report_kind" in reports.json()


def test_list_routes_require_risk_officer(client):
    for path in (
        "/v1/risk/restrictions",
        "/v1/risk/findings",
        "/v1/risk/reports",
    ):
        response = client.get(path, headers=auth("operator-token"))
        assert response.status_code == 403, path
