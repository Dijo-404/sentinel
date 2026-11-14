"""Narrow store port for AI config and run metadata."""

from __future__ import annotations

from typing import Protocol

from ..domain.types import AiConfig, AiRun


class PlatformAiStore(Protocol):
    def get_config(self, tenant_id: str) -> AiConfig | None: ...

    def put_config(self, config: AiConfig) -> AiConfig: ...

    def list_runs(self, tenant_id: str) -> tuple[AiRun, ...]: ...

    def put_run(self, run: AiRun) -> AiRun: ...
