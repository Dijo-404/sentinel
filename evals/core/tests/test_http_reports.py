"""HTTP serve: list/get RunReport rows (evaluation.v1 authority)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from sentinel_evaluation.domain.models import CONTRACT_VERSION
from sentinel_evaluation.seed import SEED_RUN_ID


def test_health_ready_capabilities(client: TestClient) -> None:
    assert client.get("/healthz").json() == {"status": "ok"}
    ready = client.get("/readyz").json()
    assert ready["status"] == "ready"
    assert ready["mode"] == "fixture"
    caps = client.get("/v1/capabilities").json()
    assert caps["contract_version"] == CONTRACT_VERSION
    assert caps["component"] == "evaluation"
    assert caps["mode"] == "fixture"
    assert caps["money_authority"] is False


def test_list_reports_returns_seeded_run_report(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = client.get("/v1/reports", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert "reports" in body
    assert len(body["reports"]) == 1
    report = body["reports"][0]
    assert report["run_id"] == SEED_RUN_ID
    assert report["contract_version"] == CONTRACT_VERSION
    assert report["status"] == "PASS"
    assert report["mode"] == "fixture"
    assert isinstance(report["checks"], list)
    assert isinstance(report["output_artifacts"], list)


def test_get_report_by_id(client: TestClient, admin_headers: dict[str, str]) -> None:
    response = client.get(f"/v1/reports/{SEED_RUN_ID}", headers=admin_headers)
    assert response.status_code == 200
    report = response.json()
    assert report["run_id"] == SEED_RUN_ID
    assert report["status"] == "PASS"


def test_get_report_missing_is_404(client: TestClient, admin_headers: dict[str, str]) -> None:
    response = client.get("/v1/reports/missing-run", headers=admin_headers)
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


def test_reports_require_bearer(client: TestClient) -> None:
    assert client.get("/v1/reports").status_code == 403
    assert client.get(f"/v1/reports/{SEED_RUN_ID}").status_code == 403


def test_operator_denied_reports(client: TestClient) -> None:
    headers = {"Authorization": "Bearer operator-token"}
    assert client.get("/v1/reports", headers=headers).status_code == 403
