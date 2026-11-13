"""Version-pinned case manifest. Pins adapters without claiming live inference determinism."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .contracts import CONTRACT_VERSION, ConfigurationError


class CaseManifest(BaseModel):
    """Pinned versions for one workflow case family."""

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
