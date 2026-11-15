"""Admin merchants list: platform_admin / sandbox-admin; seeded merchant-demo-1."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from tests.conftest import OPERATOR

from sentinel_merchant_teams.adapters.case_api_stub import StubCaseApi
from sentinel_merchant_teams.adapters.storage_memory import MemoryStaffStore
from sentinel_merchant_teams.application.errors import UnauthorizedError
from sentinel_merchant_teams.bootstrap import Settings, build_app
from sentinel_merchant_teams.domain.types import Merchant, Principal

PLATFORM_ADMIN = Principal(
    principal_id="padmin-1",
    tenant_id="tenant-demo",
    roles=("platform_admin",),
    subject_refs=("*",),
    case_ids=("*",),
)

SANDBOX_ADMIN = Principal(
    principal_id="sadmin-1",
    tenant_id="tenant-demo",
    roles=("sandbox-admin",),
    subject_refs=("merchant-demo-1", "*"),
    case_ids=("*",),
)


def _client(store: MemoryStaffStore, tokens: str) -> TestClient:
    return TestClient(
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


def test_list_merchants_returns_seeded_row(service, store):
    store.save_merchant(
        Merchant(
            tenant_id="tenant-demo",
            merchant_ref="merchant-demo-1",
            display_name="Demo Merchant",
            status="active",
        )
    )
    rows = service.list_merchants(PLATFORM_ADMIN)
    assert len(rows) == 1
    assert rows[0].merchant_ref == "merchant-demo-1"
    assert rows[0].display_name == "Demo Merchant"
    assert rows[0].status == "active"


def test_list_merchants_sandbox_admin_ok(service, store):
    store.save_merchant(
        Merchant(
            tenant_id="tenant-demo",
            merchant_ref="merchant-demo-1",
            display_name="Demo Merchant",
            status="active",
        )
    )
    rows = service.list_merchants(SANDBOX_ADMIN)
    assert [m.merchant_ref for m in rows] == ["merchant-demo-1"]


def test_list_merchants_operator_forbidden(service, store):
    store.save_merchant(
        Merchant(
            tenant_id="tenant-demo",
            merchant_ref="merchant-demo-1",
            status="active",
        )
    )
    with pytest.raises(UnauthorizedError):
        service.list_merchants(OPERATOR)


def test_http_admin_merchants_ok():
    store = MemoryStaffStore()
    store.save_merchant(
        Merchant(
            tenant_id="tenant-demo",
            merchant_ref="merchant-demo-1",
            display_name="Demo Merchant",
            status="active",
        )
    )
    tokens = (
        "platform-admin-token=padmin-1|tenant-demo|platform_admin|*|*;"
        "operator-token=op-1|tenant-demo|operator|merchant-demo-1|case-demo-42"
    )
    client = _client(store, tokens)
    response = client.get(
        "/v1/admin/merchants",
        headers={"Authorization": "Bearer platform-admin-token"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "merchants": [
            {
                "merchant_ref": "merchant-demo-1",
                "display_name": "Demo Merchant",
                "status": "active",
            }
        ]
    }


def test_http_admin_merchants_operator_403():
    store = MemoryStaffStore()
    store.save_merchant(
        Merchant(
            tenant_id="tenant-demo",
            merchant_ref="merchant-demo-1",
            status="active",
        )
    )
    tokens = "operator-token=op-1|tenant-demo|operator|merchant-demo-1|case-demo-42"
    client = _client(store, tokens)
    response = client.get(
        "/v1/admin/merchants",
        headers={"Authorization": "Bearer operator-token"},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_http_admin_merchants_sandbox_admin_ok():
    store = MemoryStaffStore()
    store.save_merchant(
        Merchant(
            tenant_id="tenant-demo",
            merchant_ref="merchant-demo-1",
            display_name="Demo Merchant",
            status="active",
        )
    )
    tokens = "sandbox-admin-token=sadmin-1|tenant-demo|sandbox-admin|merchant-demo-1,*|*"
    client = _client(store, tokens)
    response = client.get(
        "/v1/admin/merchants",
        headers={"Authorization": "Bearer sandbox-admin-token"},
    )
    assert response.status_code == 200
    assert response.json()["merchants"][0]["merchant_ref"] == "merchant-demo-1"
