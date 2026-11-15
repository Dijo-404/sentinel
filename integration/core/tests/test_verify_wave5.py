"""Wave 5 verify: body asserts fail without seed; pass with seed-shaped JSON."""

from __future__ import annotations

import pytest

from sentinel_core_assembly.adapters.verify_wave5 import (
    SEED_EVAL_RUN_ID,
    SEED_INTEGRATION_ID,
    SEED_MERCHANT_REF,
    SEED_MODEL_ID,
    SEED_POLICY_ID,
    SEED_SIGNAL_ID,
    SEED_TENANT_ID,
    assert_config_body,
    assert_health_body,
    assert_integrations_body,
    assert_merchants_body,
    assert_policies_body,
    assert_reports_body,
    assert_roles_body,
    assert_signals_body,
    assert_tenants_body,
    verify_wave5,
)


def test_seed_ids_match_peer_modules() -> None:
    assert SEED_TENANT_ID == "tenant-demo"
    assert SEED_POLICY_ID == "demo-policy-v1"
    assert SEED_MERCHANT_REF == "merchant-demo-1"
    assert SEED_MODEL_ID == "model-sandbox-1"
    assert SEED_INTEGRATION_ID == "integration-sandbox-1"
    assert SEED_EVAL_RUN_ID == "eval-sandbox-1"
    assert SEED_SIGNAL_ID == "sig-seed-request-handle"


def test_health_assert_requires_ok() -> None:
    with pytest.raises(AssertionError, match="ok"):
        assert_health_body({"status": "degraded"})
    assert_health_body({"status": "ok"})


def test_roles_assert_requires_platform_admin() -> None:
    with pytest.raises(AssertionError, match="empty"):
        assert_roles_body({"human_roles": []})
    with pytest.raises(AssertionError, match="platform_admin"):
        assert_roles_body({"human_roles": ["operator"]})
    assert_roles_body({"human_roles": ["platform_admin", "operator"]})


def test_tenants_assert_requires_demo() -> None:
    with pytest.raises(AssertionError, match="empty"):
        assert_tenants_body({"tenants": []})
    with pytest.raises(AssertionError, match="tenant-demo"):
        assert_tenants_body({"tenants": [{"tenant_id": "other"}]})
    assert_tenants_body({"tenants": [{"tenant_id": SEED_TENANT_ID, "status": "active"}]})


def test_policies_assert_requires_demo_policy() -> None:
    with pytest.raises(AssertionError, match="empty"):
        assert_policies_body({"policies": []})
    with pytest.raises(AssertionError, match="demo-policy-v1"):
        assert_policies_body({"policies": [{"policy_id": "other"}]})
    assert_policies_body({"policies": [{"policy_id": SEED_POLICY_ID, "version": SEED_POLICY_ID}]})


def test_merchants_assert_requires_demo() -> None:
    with pytest.raises(AssertionError, match="empty"):
        assert_merchants_body({"merchants": []})
    with pytest.raises(AssertionError, match="merchant-demo-1"):
        assert_merchants_body({"merchants": [{"merchant_ref": "other"}]})
    assert_merchants_body({"merchants": [{"merchant_ref": SEED_MERCHANT_REF, "status": "active"}]})


def test_config_assert_requires_seed_model() -> None:
    with pytest.raises(AssertionError, match="empty"):
        assert_config_body({"models": [], "kill_switch": False})
    with pytest.raises(AssertionError, match="model-sandbox-1"):
        assert_config_body({"models": [{"model_id": "other"}], "kill_switch": False})
    with pytest.raises(AssertionError, match="kill_switch"):
        assert_config_body({"models": [{"model_id": SEED_MODEL_ID}]})
    assert_config_body({"models": [{"model_id": SEED_MODEL_ID}], "kill_switch": False})


def test_integrations_assert_requires_seed() -> None:
    with pytest.raises(AssertionError, match="empty"):
        assert_integrations_body({"integrations": []})
    with pytest.raises(AssertionError, match="integration-sandbox-1"):
        assert_integrations_body({"integrations": [{"integration_id": "other"}]})
    assert_integrations_body(
        {"integrations": [{"integration_id": SEED_INTEGRATION_ID, "status": "ACTIVE"}]}
    )


def test_reports_assert_requires_seed() -> None:
    with pytest.raises(AssertionError, match="empty"):
        assert_reports_body({"reports": []})
    with pytest.raises(AssertionError, match="eval-sandbox-1"):
        assert_reports_body({"reports": [{"run_id": "other"}]})
    assert_reports_body({"reports": [{"run_id": SEED_EVAL_RUN_ID}]})


def test_signals_assert_requires_seed_and_non_financial() -> None:
    with pytest.raises(AssertionError, match="financial_audit"):
        assert_signals_body({"signals": [{"signal_id": SEED_SIGNAL_ID}], "financial_audit": True})
    with pytest.raises(AssertionError, match="empty"):
        assert_signals_body({"signals": [], "financial_audit": False})
    with pytest.raises(AssertionError, match="sig-seed-request-handle"):
        assert_signals_body({"signals": [{"signal_id": "other"}], "financial_audit": False})
    assert_signals_body({"signals": [{"signal_id": SEED_SIGNAL_ID}], "financial_audit": False})


def test_verify_wave5_fails_closed_when_peers_down(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VERIFY_IDENTITY_URL", "http://127.0.0.1:1")
    monkeypatch.setenv("VERIFY_POLICY_URL", "http://127.0.0.1:1")
    monkeypatch.setenv("VERIFY_MERCHANT_TEAMS_URL", "http://127.0.0.1:1")
    monkeypatch.setenv("VERIFY_PLATFORM_AI_URL", "http://127.0.0.1:1")
    monkeypatch.setenv("VERIFY_EVALS_URL", "http://127.0.0.1:1")
    monkeypatch.setenv("VERIFY_OBSERVABILITY_URL", "http://127.0.0.1:1")
    report = verify_wave5(dict(__import__("os").environ))
    assert report["status"] == "FAIL"
    assert report.get("reason_code") == "WAVE5_VERIFY_FAILED"
    assert any(not c.get("ok") for c in report["checks"])
