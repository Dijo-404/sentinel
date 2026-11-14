"""Sandbox seed gate: refuse non-demo tenants / non-sandbox runs."""

from __future__ import annotations

from sentinel_core_assembly.adapters.seed_sandbox import seed_sandbox


def test_seed_refuses_non_demo_tenant() -> None:
    report = seed_sandbox(
        {
            "CORE_ASSEMBLY_TENANT_ID": "tenant-prod",
            "SENTINEL_V1_SANDBOX": "1",
        }
    )
    assert report["status"] == "FAIL"
    assert report["reason_code"] == "SANDBOX_TENANT_REQUIRED"
    assert report["seeds"] == []


def test_seed_refuses_when_sandbox_flag_missing() -> None:
    report = seed_sandbox(
        {
            "CORE_ASSEMBLY_TENANT_ID": "tenant-demo",
            "SENTINEL_V1_SANDBOX": "0",
        }
    )
    assert report["status"] == "FAIL"
    assert report["reason_code"] == "SANDBOX_FLAG_REQUIRED"
    assert report["seeds"] == []


def test_seed_pass_with_documented_peer_skips() -> None:
    report = seed_sandbox(
        {
            "CORE_ASSEMBLY_TENANT_ID": "tenant-demo",
            "SENTINEL_V1_SANDBOX": "1",
        }
    )
    assert report["status"] == "PASS"
    assert report.get("reason_code") is None
    assert isinstance(report["seeds"], list)
    assert any(entry.get("status") == "SKIPPED" for entry in report["seeds"])
