"""SN-041 fixture RBAC probes — path=rbac-fixture, no SN-009 money claim."""

from __future__ import annotations

from sentinel_core_assembly.adapters.rbac_fixture import RbacFixtureProbe
from sentinel_core_assembly.adapters.sandbox_matrix import (
    default_peer_endpoints,
    default_tokens,
    load_assembly_matrix,
    load_identity_matrix,
    optional_rbac_peer_endpoints,
    rbac_path_label,
    sn009_authority_exercised,
)


def test_matrix_includes_identity_and_risk_ports() -> None:
    identity = load_identity_matrix()
    ports = dict(identity.get("ports", {}))
    assert ports.get("identity") == 8012
    assert ports.get("risk") == 8013
    assembly = load_assembly_matrix()
    urls = dict(assembly.get("base_urls", {}))
    assert urls["identity.v1"] == "http://127.0.0.1:8012"
    assert urls["risk.v1"] == "http://127.0.0.1:8013"
    optional = optional_rbac_peer_endpoints()
    assert optional["identity.v1"].endswith(":8012")
    assert optional["risk.v1"].endswith(":8013")
    # Money-path defaults stay free of optional RBAC peers.
    endpoints = default_peer_endpoints()
    assert "identity.v1" not in endpoints
    assert "risk.v1" not in endpoints
    tokens = default_tokens()
    assert tokens["operator"] == "tok-operator"
    assert tokens["platform_admin"] == "tok-platform-admin"
    assert tokens["risk_officer"] == "tok-risk-officer"
    assert sn009_authority_exercised() is False
    assert assembly.get("sn009_authority_exercised") is False
    assert rbac_path_label() == "rbac-fixture"


def test_auth01_customer_register_denied_staff_role() -> None:
    probe = RbacFixtureProbe()
    outcome = probe.customer_register(
        email="sneaky@example.test",
        password="demo-password-not-secret",
        display_name="Sneaky",
        extra_fields={"role": "admin"},
    )
    assert outcome["status_code"] == 422
    assert outcome["denied"] is True
    assert outcome["account_created"] is False
    assert outcome["path"] == "rbac-fixture"
    assert outcome["sn009_authority_exercised"] is False
    assert "sneaky@example.test" not in probe.world.accounts


def test_admin_invite_staff() -> None:
    probe = RbacFixtureProbe()
    outcome = probe.admin_invite_staff(
        actor_role="platform_admin",
        work_email="new-op@example.test",
        role_id="operator",
    )
    assert outcome["status_code"] == 201
    assert outcome["invitation_created"] is True
    assert outcome["role_id"] == "operator"
    assert outcome["path"] == "rbac-fixture"
    assert outcome["sn009_authority_exercised"] is False
    assert outcome["invitation_id"] in probe.world.invitations


def test_auth06_operator_denied_supervisor_decide() -> None:
    probe = RbacFixtureProbe()
    outcome = probe.decide(actor_role="operator", action_id="action-auth06")
    assert outcome["status_code"] == 403
    assert outcome["denied"] is True
    assert outcome["ledger_called"] is False
    assert outcome["ledger_decision_count"] == 0
    assert probe.world.ledger_decision_calls == []
    assert outcome["path"] == "rbac-fixture"
    assert outcome["sn009_authority_exercised"] is False


def test_run_auth_probes_bundle_passes_with_honest_labels() -> None:
    probe = RbacFixtureProbe()
    report = probe.run_auth_probes()
    assert report["probes_passed"] is True
    assert report["path"] == "rbac-fixture"
    assert report["sn009_authority_exercised"] is False
    assert report["auth01_register_denied"]["denied"] is True
    assert report["admin_invite_staff"]["invitation_created"] is True
    assert report["auth06_operator_decide"]["status_code"] == 403
    caps = probe.capabilities_by_port()
    assert set(caps) >= {"identity.v1", "risk.v1", "case-api.v1"}
    assert all(c.mode == "fixture" for c in caps.values())
