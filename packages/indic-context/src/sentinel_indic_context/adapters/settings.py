"""Module-local settings. Live mode is opt-in."""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="INDIC_CONTEXT_", env_file=".env", extra="ignore")

    mode: Literal["fake", "live"] = "fake"
    fake_scenario: str = "proposal"
    host: str = "127.0.0.1"
    port: int = 8091
    policy_version: str = "demo-policy-v1"
    contract_version: str = "sentinel.task-contracts.v1"
    native_review_limit: str = "human-review-required-for-refunds"
    auth_tokens: str = Field(
        default=(
            '{"workflow-token":{"principal_id":"svc-workflow","tenant_id":"tenant-demo",'
            '"roles":["workflow"],"subject_refs":["subject-demo"],"case_ids":["case-demo-42"]}}'
        )
    )
    sarvam_base_url: str = "https://api.sarvam.ai"
    sarvam_model_id: str = "sarvam-m"
    sarvam_api_key: str = ""
    sarvam_timeout_seconds: float = 20.0

    def token_map_raw(self) -> dict[str, Any]:
        return json.loads(self.auth_tokens)
