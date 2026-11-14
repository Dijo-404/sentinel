"""Merchant settings: GET returns seeded row; missing/unauthorized fail closed."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from tests.conftest import OPERATOR, OUTSIDER

from sentinel_merchant_teams.adapters.case_api_stub import StubCaseApi
from sentinel_merchant_teams.adapters.storage_memory import MemoryStaffStore
from sentinel_merchant_teams.application.errors import NotFoundError, UnauthorizedError
from sentinel_merchant_teams.bootstrap import Settings, build_app
from sentinel_merchant_teams.domain.types import MerchantSettings


def test_get_settings_returns_saved_row(service, store):
    row = MerchantSettings(
        tenant_id="tenant-demo",
        merchant_ref="merchant-demo-1",
        notification_language="en",
        notify_disputes=True,
        notify_settlements=True,
    )
    store.save_settings(row)
    got = service.get_settings(OPERATOR, "merchant-demo-1")
    assert got.tenant_id == "tenant-demo"
    assert got.merchant_ref == "merchant-demo-1"
    assert got.notification_language == "en"
    assert got.notify_disputes is True
    assert got.notify_settlements is True


def test_get_settings_missing_fails_closed(service):
    with pytest.raises(NotFoundError):
        service.get_settings(OPERATOR, "merchant-demo-1")


def test_get_settings_unauthorized_scope(service, store):
    store.save_settings(
        MerchantSettings(
            tenant_id="tenant-demo",
            merchant_ref="merchant-demo-1",
            notification_language="en",
            notify_disputes=True,
            notify_settlements=False,
        )
    )
    with pytest.raises(UnauthorizedError):
        service.get_settings(OUTSIDER, "merchant-demo-1")


def test_http_get_settings_ok():
    store = MemoryStaffStore()
    store.save_settings(
        MerchantSettings(
            tenant_id="tenant-demo",
            merchant_ref="merchant-demo-1",
            notification_language="hi",
            notify_disputes=False,
            notify_settlements=True,
        )
    )
    tokens = (
        "operator-token=op-1|tenant-demo|operator|merchant-demo-1|case-demo-42;"
        "supervisor-token=sup-1|tenant-demo|supervisor|merchant-demo-1,*|case-demo-42"
    )
    client = TestClient(
        build_app(
            Settings(
                mode="fixture",
                tokens=tokens,
                case_api_base_url="",
                case_api_token="",
                identity_base_url="",
                identity_token="",
                contract_version="sentinel.task-contracts.v1",
            ),
            store=store,
            cases=StubCaseApi(mode="valid"),
            identity=None,
        )
    )
    response = client.get(
        "/v1/merchant/settings",
        params={"merchant_ref": "merchant-demo-1"},
        headers={"Authorization": "Bearer operator-token"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "tenant_id": "tenant-demo",
        "merchant_ref": "merchant-demo-1",
        "notification_language": "hi",
        "notify_disputes": False,
        "notify_settlements": True,
    }


def test_http_get_settings_missing_404():
    tokens = "operator-token=op-1|tenant-demo|operator|merchant-demo-1|case-demo-42"
    client = TestClient(
        build_app(
            Settings(
                mode="fixture",
                tokens=tokens,
                case_api_base_url="",
                case_api_token="",
                identity_base_url="",
                identity_token="",
                contract_version="sentinel.task-contracts.v1",
            ),
            store=MemoryStaffStore(),
            cases=StubCaseApi(mode="valid"),
            identity=None,
        )
    )
    response = client.get(
        "/v1/merchant/settings",
        params={"merchant_ref": "merchant-demo-1"},
        headers={"Authorization": "Bearer operator-token"},
    )
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"
