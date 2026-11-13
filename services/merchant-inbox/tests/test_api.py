"""HTTP surface smoke for capabilities and get enrichment."""

from __future__ import annotations

from fastapi.testclient import TestClient

from sentinel_merchant_inbox import CONTRACT_SHA256, CONTRACT_VERSION


def test_capabilities(client: TestClient) -> None:
    response = client.get("/v1/capabilities")
    assert response.status_code == 200
    body = response.json()
    assert body["contract_version"] == CONTRACT_VERSION
    assert body["component"] == "merchant-inbox"
    assert body["mode"] == "fixture"
    assert body["port"] == "merchant-inbox.v1"


def test_health_ready(client: TestClient) -> None:
    assert client.get("/healthz").status_code == 200
    assert client.get("/readyz").json()["mode"] == "fixture"


def test_contract_hash_pinned() -> None:
    assert CONTRACT_SHA256 == "0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb"


def test_get_enriches_case_linked_item(client: TestClient, merchant_auth: dict[str, str]) -> None:
    response = client.get(
        "/v1/exceptions/exc-paid-unfulfilled-1",
        headers=merchant_auth,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["case"]["case_id"] == "case-demo-42"
    assert body["evidence"]["case_id"] == "case-demo-42"
    assert body["resolved"] is False


def test_get_unmatched_without_case(client: TestClient, merchant_auth: dict[str, str]) -> None:
    response = client.get(
        "/v1/exceptions/exc-unmatched-1",
        headers=merchant_auth,
    )
    assert response.status_code == 200
    body = response.json()
    assert "case_id" not in body or body.get("case_id") is None
    assert "case" not in body
