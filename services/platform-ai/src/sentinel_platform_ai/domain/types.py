"""Framework-free wire-aligned types for platform-ai.v1 (metadata only)."""

from __future__ import annotations

from dataclasses import dataclass

CONTRACT_VERSION = "sentinel.task-contracts.v1"
CONTRACT_SHA256 = "0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb"

ADMIN_ROLES = frozenset({"platform_admin", "sandbox-admin"})


@dataclass(frozen=True, slots=True)
class Principal:
    principal_id: str
    tenant_id: str
    roles: tuple[str, ...]
    subject_refs: tuple[str, ...] = ()
    case_ids: tuple[str, ...] = ()

    def is_platform_admin(self) -> bool:
        return bool(ADMIN_ROLES & set(self.roles))


@dataclass(frozen=True, slots=True)
class AiModel:
    model_id: str
    label: str
    provider: str

    def to_wire(self) -> dict[str, str]:
        return {
            "model_id": self.model_id,
            "label": self.label,
            "provider": self.provider,
        }


@dataclass(frozen=True, slots=True)
class AiConfig:
    tenant_id: str
    models: tuple[AiModel, ...]
    kill_switch: bool
    updated_at: str

    def to_wire(self) -> dict:
        return {
            "models": [model.to_wire() for model in self.models],
            "kill_switch": self.kill_switch,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True, slots=True)
class AiRun:
    run_id: str
    tenant_id: str
    model_id: str
    status: str
    started_at: str

    def to_wire(self) -> dict[str, str]:
        return {
            "run_id": self.run_id,
            "model_id": self.model_id,
            "status": self.status,
            "started_at": self.started_at,
        }


@dataclass(frozen=True, slots=True)
class AiIntegration:
    integration_id: str
    tenant_id: str
    name: str
    status: str
    updated_at: str

    def to_wire(self) -> dict[str, str]:
        return {
            "integration_id": self.integration_id,
            "name": self.name,
            "status": self.status,
            "updated_at": self.updated_at,
        }
