"""SN-040: extended human roles never satisfy supervisor decide gates."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sentinel_action_ledger.adapters.auth_tokens import demo_principals
from sentinel_action_ledger.application.service import _require_roles
from sentinel_action_ledger.domain.errors import ForbiddenError
from sentinel_action_ledger.domain.types import Principal

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "contracts" / "principals.json"


@pytest.mark.parametrize(
    "token",
    [
        "token-risk-officer-demo",
        "token-platform-admin-demo",
        "token-merchant-demo",
        "tok-risk-officer",
        "tok-platform-admin",
        "tok-merchant",
    ],
)
def test_extended_human_tokens_resolve_without_supervisor(token: str) -> None:
    mapping = demo_principals()
    principal = mapping[token]
    assert not principal.has_role("supervisor")
    for service_role in ("workflow", "dispatcher", "verifier"):
        assert not principal.has_role(service_role)
    with pytest.raises(ForbiddenError, match="Role not permitted"):
        _require_roles(principal, "supervisor")


@pytest.mark.parametrize("role", ["risk_officer", "platform_admin", "merchant"])
def test_extended_role_principal_cannot_decide(role: str) -> None:
    principal = Principal(f"{role}-x", "tenant-demo", (role,), ("*",), ("*",))
    with pytest.raises(ForbiddenError):
        _require_roles(principal, "supervisor")


def test_catalog_marks_money_forbidden_roles() -> None:
    payload = json.loads(CATALOG.read_text(encoding="utf-8"))
    assert payload["catalog_extension"] == "sn-040-human-roles.v1"
    forbidden = set(payload["money_forbidden_human_roles"])
    assert {"merchant", "risk_officer", "platform_admin"} <= forbidden
    assert payload["money_authority"]["human_decide"] == ["supervisor"]
    for role in ("merchant", "risk_officer", "platform_admin"):
        entry = next(p for p in payload["principals"].values() if role in p["roles"])
        assert "supervisor" not in entry["roles"]
