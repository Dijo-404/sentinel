"""Use cases: read AI config, run, and integration metadata for a tenant."""

from __future__ import annotations

from ..domain.types import AiConfig, AiIntegration, AiRun, Principal
from .errors import NotFoundError, UnauthorizedError
from .ports import PlatformAiStore


class PlatformAiService:
    def __init__(self, store: PlatformAiStore) -> None:
        self._store = store

    def get_config(self, principal: Principal) -> AiConfig:
        _require_admin(principal)
        config = self._store.get_config(principal.tenant_id)
        if config is None:
            raise NotFoundError("AI config not found for tenant")
        return config

    def list_runs(self, principal: Principal) -> tuple[AiRun, ...]:
        _require_admin(principal)
        return self._store.list_runs(principal.tenant_id)

    def list_integrations(self, principal: Principal) -> tuple[AiIntegration, ...]:
        _require_admin(principal)
        return self._store.list_integrations(principal.tenant_id)


def _require_admin(principal: Principal) -> None:
    if not principal.is_platform_admin():
        raise UnauthorizedError("platform admin role required")
