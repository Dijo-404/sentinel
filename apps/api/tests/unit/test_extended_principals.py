"""SN-040: risk_officer / platform_admin / merchant are not supervisors."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sentinel_api.application.authz import require_roles
from sentinel_api.domain.types import DomainError, Principal

ROOT = Path(__file__).resolve().parents[2]
TOKENS = ROOT / "fixtures" / "auth_tokens.json"


def _principal(roles: tuple[str, ...]) -> Principal:
    return Principal(
        principal_id="p-ext",
        tenant_id="tenant-demo",
        roles=roles,
        subject_refs=(),
        case_ids=(),
    )


@pytest.mark.parametrize("role", ["risk_officer", "platform_admin", "merchant"])
def test_extended_roles_fail_supervisor_require(role: str) -> None:
    with pytest.raises(DomainError) as exc:
        require_roles(_principal(roles=(role,)), "supervisor")
    assert exc.value.code == "FORBIDDEN"
    assert exc.value.http_status == 403


def test_fixture_catalog_includes_extended_humans() -> None:
    payload = json.loads(TOKENS.read_text(encoding="utf-8"))
    for key, role in (
        ("token-risk-officer", "risk_officer"),
        ("token-platform-admin", "platform_admin"),
        ("token-merchant", "merchant"),
    ):
        assert role in payload[key]["roles"]
        assert "supervisor" not in payload[key]["roles"]
