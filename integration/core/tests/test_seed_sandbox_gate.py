"""Sandbox seed gate: refuse non-demo tenants / non-sandbox runs; peer make hooks."""

from __future__ import annotations

from sentinel_core_assembly.adapters.seed_sandbox import SeedEntry, seed_sandbox


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


def test_seed_pass_with_documented_peer_skips_without_db_urls() -> None:
    report = seed_sandbox(
        {
            "CORE_ASSEMBLY_TENANT_ID": "tenant-demo",
            "SENTINEL_V1_SANDBOX": "1",
        }
    )
    assert report["status"] == "PASS"
    assert report.get("reason_code") is None
    assert isinstance(report["seeds"], list)
    by_peer = {entry["peer"]: entry for entry in report["seeds"]}
    assert by_peer["merchant-analytics"]["status"] == "SKIPPED"
    assert by_peer["merchant-disputes"]["status"] == "SKIPPED"
    assert by_peer["risk"]["status"] == "SKIPPED"
    assert "MERCHANT_ANALYTICS_DATABASE_URL" in by_peer["merchant-analytics"]["detail"]
    assert any(entry.get("status") == "SKIPPED" for entry in report["seeds"])


def test_seed_invokes_wave0_1_peers_when_database_urls_set() -> None:
    calls: list[tuple[str, str]] = []

    def fake_invoke(peer: str, rel_dir: str, env: dict, **_kwargs: object) -> SeedEntry:
        calls.append((peer, rel_dir))
        return {
            "peer": peer,
            "rows": 1,
            "status": "PASS",
            "detail": "make seed ok",
        }

    report = seed_sandbox(
        {
            "CORE_ASSEMBLY_TENANT_ID": "tenant-demo",
            "SENTINEL_V1_SANDBOX": "1",
            "MERCHANT_ANALYTICS_DATABASE_URL": "postgresql+psycopg://x/y",
            "DISPUTES_DATABASE_URL": "postgresql+psycopg://x/y",
            "RISK_DATABASE_URL": "postgresql+psycopg://x/y",
        },
        invoke_peer_seed=fake_invoke,
    )
    assert report["status"] == "PASS"
    assert [c[0] for c in calls] == [
        "merchant-analytics",
        "merchant-disputes",
        "risk",
    ]
    by_peer = {entry["peer"]: entry for entry in report["seeds"]}
    assert by_peer["merchant-analytics"]["status"] == "PASS"
    assert by_peer["merchant-disputes"]["rows"] == 1
    assert by_peer["risk"]["status"] == "PASS"
    assert by_peer["case-api"]["status"] == "SKIPPED"


def test_seed_fails_when_peer_make_seed_fails() -> None:
    def fake_invoke(peer: str, rel_dir: str, env: dict, **_kwargs: object) -> SeedEntry:
        return {
            "peer": peer,
            "rows": 0,
            "status": "FAIL",
            "detail": "boom",
        }

    report = seed_sandbox(
        {
            "CORE_ASSEMBLY_TENANT_ID": "tenant-demo",
            "SENTINEL_V1_SANDBOX": "1",
            "RISK_DATABASE_URL": "postgresql+psycopg://x/y",
        },
        invoke_peer_seed=fake_invoke,
    )
    assert report["status"] == "FAIL"
    assert report["reason_code"] == "PEER_SEED_FAILED"
