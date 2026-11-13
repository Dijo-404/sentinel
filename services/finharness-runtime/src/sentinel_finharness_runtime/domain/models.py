"""Pinned wire/domain types for finharness-runtime.v1."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .errors import ConfigurationError
from .rules import case_in_rollout

CONTRACT_VERSION = "sentinel.task-contracts.v1"
CONTRACT_SHA256 = "0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa"
PORT = "finharness-runtime.v1"

ExecutionMode = Literal["legacy", "shadow", "harness"]
EvidenceMode = Literal["fixture", "real-peers"]


class RuntimeConfig(BaseModel):
    """Version-pinned switches. Writes/notifications off unless explicitly enabled."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal["sentinel.task-contracts.v1"] = CONTRACT_VERSION
    runtime_version: str = Field(default="finharness-runtime.v1", min_length=1)
    enabled: bool = False
    execution_mode: ExecutionMode = "legacy"
    financial_writes: bool = False
    notifications: bool = False
    rollout_percent: int = Field(default=0, ge=0, le=100)
    allowed_workflows: tuple[str, ...] = ()
    allowed_tenants: tuple[str, ...] = ()
    sandbox_only: bool = True

    @field_validator("contract_version")
    @classmethod
    def _pin_contract(cls, value: str) -> str:
        if value != CONTRACT_VERSION:
            raise ConfigurationError(f"contract_version must be {CONTRACT_VERSION}, got {value!r}")
        return value

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any] | None = None) -> RuntimeConfig:
        return cls.model_validate(dict(raw or {}))

    def routing_active(self) -> bool:
        return self.enabled and self.execution_mode in {"shadow", "harness"}

    def allows_workflow(self, workflow: str) -> bool:
        return not self.allowed_workflows or workflow in self.allowed_workflows

    def allows_tenant(self, tenant_id: str) -> bool:
        return not self.allowed_tenants or tenant_id in self.allowed_tenants

    def case_eligible_for_new_routing(self, case_id: str) -> bool:
        if not self.routing_active():
            return False
        return case_in_rollout(case_id, self.rollout_percent)


class CaseManifest(BaseModel):
    """Pinned adapter/workflow versions for one case family."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal["sentinel.task-contracts.v1"] = CONTRACT_VERSION
    workflow_name: str = Field(min_length=1)
    workflow_version: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)
    evidence_mapper_version: str = Field(min_length=1)
    model_adapter_version: str = Field(min_length=1)
    verifier_version: str = Field(min_length=1)
    indic_context_version: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    allowed_action_types: tuple[str, ...] = ("REQUEST_REFUND",)
    max_model_calls: int = Field(default=4, ge=1, le=32)
    max_read_tool_calls: int = Field(default=12, ge=1, le=64)
    max_investigation_seconds: int = Field(default=20, ge=1, le=300)

    @field_validator("contract_version")
    @classmethod
    def _pin_contract(cls, value: str) -> str:
        if value != CONTRACT_VERSION:
            raise ConfigurationError(f"contract_version must be {CONTRACT_VERSION}, got {value!r}")
        return value

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> CaseManifest:
        return cls.model_validate(dict(raw))


class CasePin(BaseModel):
    """Durable per-case runtime pin. Survives config switch and process restart."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str
    tenant_id: str
    runtime_version: str
    workflow_name: str
    workflow_version: str
    execution_mode: ExecutionMode
    pinned_at: str
    manifest: CaseManifest


class UnknownAction(BaseModel):
    """Outstanding ambiguous command. Reconciliation uses the original provider_ref."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    action_id: str
    case_id: str
    provider_ref: str
    status: str = "OUTCOME_UNKNOWN"
    recorded_at: str


class ShadowComparison(BaseModel):
    """Read-only proposal/outcome comparison. Never a financial write receipt."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal["sentinel.task-contracts.v1"] = CONTRACT_VERSION
    port: Literal["finharness-runtime.v1"] = PORT
    baseline_sha256: str = CONTRACT_SHA256
    case_id: str
    runtime_version: str
    evidence_mode: EvidenceMode
    baseline_proposal: dict[str, Any]
    candidate_proposal: dict[str, Any]
    proposals_match: bool
    write_adapter_present: bool = False
    credentials_present: bool = False
    notifications_attempted: int = 0
    refund_write_attempts: int = 0
    reason_codes: tuple[str, ...] = ()


class ReconcileResult(BaseModel):
    """Status lookup by original stable provider reference. Never mints a new refund ID."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    action_id: str
    provider_ref: str
    status: str
    minted_new_refund: bool = False
    financial_writes_enabled: bool


class RouteDecision(BaseModel):
    """Guarded sandbox/harness routing decision for a case."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str
    routed: bool
    execution_mode: ExecutionMode
    runtime_version: str
    financial_writes: bool
    reason_code: str
