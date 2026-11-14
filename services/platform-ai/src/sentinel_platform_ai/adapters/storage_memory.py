"""In-memory platform-ai store for fixture mode and unit tests."""

from __future__ import annotations

from ..domain.types import AiConfig, AiRun


class MemoryPlatformAiStore:
    def __init__(self) -> None:
        self._configs: dict[str, AiConfig] = {}
        self._runs: dict[str, AiRun] = {}

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
