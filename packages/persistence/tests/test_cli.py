import json
import os
import subprocess
import sys


def cli(operation, engine=None, service=None, **overrides):
    env = {
        key: value
        for key, value in os.environ.items()
        if key != "DATABASE_URL" and not key.startswith("PERSISTENCE_")
    }
    env.update(PERSISTENCE_ENVIRONMENT="sandbox")
    if engine is not None:
        env["DATABASE_URL"] = engine.url.render_as_string(hide_password=False)
    if service:
        env.update(PERSISTENCE_SCHEMA=service.schema, PERSISTENCE_RUNTIME_ROLE=service.runtime_role)
    env.update(overrides)
    return subprocess.run(
        [sys.executable, "-m", "sentinel_persistence", operation],
        env=env,
        text=True,
        capture_output=True,
        timeout=20,
    )


def test_cli_missing_or_malformed_configuration_is_redacted():
    for extra in (
        {},
        {"DATABASE_URL": "private-secret-malformed-url"},
        {"PERSISTENCE_CONTRACT_VERSION": "incompatible-v2"},
    ):
        result = cli("inspect", **extra)
        assert result.returncode == 2
        assert "private-secret" not in result.stdout + result.stderr
        assert "configuration" in result.stderr.lower()


def test_cli_real_database_roundtrip(services, postgres):
    with services("cli") as service:
        for command, engine in (("migrate", service.owner), ("seed", postgres)):
            result = cli(command, engine, service)
            assert result.returncode == 0, result.stderr
        result = cli("inspect", service.runtime, service, PERSISTENCE_TENANT_ID="demo-tenant-a")
        assert result.returncode == 0, result.stderr
        report = json.loads(result.stdout)
        assert report["tenant_records"] == 1
        assert report["migration_revision"] == "0001_demo_notes"
        assert report["contract_version"] == "sentinel.task-contracts.v1"
        assert report["port"] == "persistence-kit.v1"
        assert report["evidence_mode"] == "real-postgresql/synthetic-records"
        incompatible = cli(
            "inspect",
            service.runtime,
            service,
            PERSISTENCE_TENANT_ID="demo-tenant-a",
            PERSISTENCE_CONTRACT_VERSION="incompatible-v2",
        )
        assert incompatible.returncode == 2
        result = cli("reset", postgres, service)
        assert result.returncode == 0, result.stderr
        result = cli("inspect", service.runtime, service, PERSISTENCE_TENANT_ID="demo-tenant-a")
        assert json.loads(result.stdout)["tenant_records"] == 0


def test_cli_unavailable_database_reports_failure_without_credentials(services, postgres):
    with services("down") as service:
        url = postgres.url.set(port=1, password="private-database-secret")
        result = cli(
            "inspect",
            postgres,
            service,
            DATABASE_URL=url.render_as_string(False),
            PERSISTENCE_TENANT_ID="demo-tenant-a",
        )
        assert result.returncode == 1
        assert "database" in result.stderr.lower()
        assert "private-database-secret" not in result.stdout + result.stderr
