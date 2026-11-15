"""Sandbox seed: AI config + run + integration metadata for tenant-demo."""

from __future__ import annotations

from typing import Any

from .adapters.storage_postgres import PostgresPlatformAiStore, build_engine
from .application.errors import ConfigurationError
from .domain.types import AiConfig, AiIntegration, AiModel, AiRun

SANDBOX_TENANT = "tenant-demo"
SEED_TENANT_ID = SANDBOX_TENANT
SEED_MODEL_ID = "model-sandbox-1"
SEED_RUN_ID = "run-demo-1"
SEED_INTEGRATION_ID = "integration-sandbox-1"
SEED_CONFIG_UPDATED_AT = "2026-11-15T00:00:00Z"
SEED_RUN_STARTED_AT = "2026-11-15T00:01:00Z"
SEED_INTEGRATION_UPDATED_AT = "2026-11-15T00:02:00Z"
SEED_INTEGRATION_NAME = "Sandbox webhook"
SEED_INTEGRATION_STATUS = "ACTIVE"


def seed_demo_platform_ai(database_url: str) -> dict[str, Any]:
    """Write synthetic config + run + integration into Postgres."""
    if not (database_url or "").strip():
        raise ConfigurationError("PLATFORM_AI_DATABASE_URL is required for seed")

    engine = build_engine(database_url)
    try:
        store = PostgresPlatformAiStore(engine)
        store.migrate()
        config = AiConfig(
            tenant_id=SEED_TENANT_ID,
            models=(
                AiModel(
                    model_id=SEED_MODEL_ID,
                    label="Sandbox chat",
                    provider="sandbox",
                ),
            ),
            kill_switch=False,
            updated_at=SEED_CONFIG_UPDATED_AT,
        )
        run = AiRun(
            run_id=SEED_RUN_ID,
            tenant_id=SEED_TENANT_ID,
            model_id=SEED_MODEL_ID,
            status="SUCCEEDED",
            started_at=SEED_RUN_STARTED_AT,
        )
        integration = AiIntegration(
            integration_id=SEED_INTEGRATION_ID,
            tenant_id=SEED_TENANT_ID,
            name=SEED_INTEGRATION_NAME,
            status=SEED_INTEGRATION_STATUS,
            updated_at=SEED_INTEGRATION_UPDATED_AT,
        )
        store.put_config(config)
        store.put_run(run)
        store.put_integration(integration)
        loaded_config = store.get_config(SEED_TENANT_ID)
        loaded_runs = store.list_runs(SEED_TENANT_ID)
        loaded_integrations = store.list_integrations(SEED_TENANT_ID)
        if loaded_config is None:
            raise ConfigurationError("seed missing AI config row")
        if not any(r.run_id == SEED_RUN_ID for r in loaded_runs):
            raise ConfigurationError(f"seed missing run {SEED_RUN_ID!r}")
        if not any(i.integration_id == SEED_INTEGRATION_ID for i in loaded_integrations):
            raise ConfigurationError(f"seed missing integration {SEED_INTEGRATION_ID!r}")
    finally:
        engine.dispose()

    return {
        "status": "PASS",
        "peer": "platform-ai",
        "tenant_id": SEED_TENANT_ID,
        "model_id": SEED_MODEL_ID,
        "run_id": SEED_RUN_ID,
        "integration_id": SEED_INTEGRATION_ID,
        "rows": 3,
        "evidence_label": "synthetic-sandbox",
    }
