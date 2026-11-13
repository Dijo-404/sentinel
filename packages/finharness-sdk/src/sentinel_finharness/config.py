"""Runtime configuration. Routing, financial writes, and notifications are off by default."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .contracts import CONTRACT_VERSION, ConfigurationError

ExecutionMode = Literal["legacy", "shadow", "harness"]


class RuntimeConfig(BaseModel):
    """Version-pinned FinHarness switches. Defaults keep legacy Sentinel path authoritative."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal["sentinel.task-contracts.v1"] = CONTRACT_VERSION
    enabled: bool = False
    execution_mode: ExecutionMode = "legacy"
    financial_writes: bool = False
    notifications: bool = False
    rollout_percent: int = Field(default=0, ge=0, le=100)
    allowed_workflows: tuple[str, ...] = ()
    allowed_tenants: tuple[str, ...] = ()

    @field_validator("contract_version")
    @classmethod
    def _pin_contract(cls, value: str) -> str:
        if value != CONTRACT_VERSION:
            raise ConfigurationError(f"contract_version must be {CONTRACT_VERSION}, got {value!r}")
        return value

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any] | None = None) -> RuntimeConfig:
        data = dict(raw or {})
        return cls.model_validate(data)

    def routing_active(self) -> bool:
        return self.enabled and self.execution_mode in {"shadow", "harness"}

    def allows_workflow(self, workflow: str) -> bool:
        return not self.allowed_workflows or workflow in self.allowed_workflows

    def allows_tenant(self, tenant_id: str) -> bool:
        return not self.allowed_tenants or tenant_id in self.allowed_tenants
