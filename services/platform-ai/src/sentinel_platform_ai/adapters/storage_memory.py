"""In-memory platform-ai store for fixture mode and unit tests."""

from __future__ import annotations

from ..domain.types import AiConfig, AiIntegration, AiRun


class MemoryPlatformAiStore:
    def __init__(self) -> None:
        self._configs: dict[str, AiConfig] = {}
        self._runs: dict[str, AiRun] = {}
        self._integrations: dict[str, AiIntegration] = {}

    def get_config(self, tenant_id: str) -> AiConfig | None:
        return self._configs.get(tenant_id)

    def put_config(self, config: AiConfig) -> AiConfig:
        self._configs[config.tenant_id] = config
        return config

    def list_runs(self, tenant_id: str) -> tuple[AiRun, ...]:
        items = [run for run in self._runs.values() if run.tenant_id == tenant_id]
        return tuple(sorted(items, key=lambda r: r.started_at, reverse=True))

    def put_run(self, run: AiRun) -> AiRun:
        self._runs[run.run_id] = run
        return run

    def list_integrations(self, tenant_id: str) -> tuple[AiIntegration, ...]:
        items = [item for item in self._integrations.values() if item.tenant_id == tenant_id]
        return tuple(sorted(items, key=lambda i: i.updated_at, reverse=True))

    def put_integration(self, integration: AiIntegration) -> AiIntegration:
        self._integrations[integration.integration_id] = integration
        return integration
