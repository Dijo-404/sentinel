"""Module-local settings. Real peer URLs are opt-in."""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MERCHANT_COMMS_", env_file=".env", extra="ignore")

    mode: Literal["fixture", "real-peers"] = "fixture"
    host: str = "127.0.0.1"
    port: int = 8093
    contract_version: str = "sentinel.task-contracts.v1"
    default_channel: str = "merchant-portal"
    auth_tokens: str = Field(
        default=(
            '{"operator-token":{"principal_id":"op-demo","tenant_id":"tenant-demo",'
            '"roles":["operator"],"subject_refs":["subject-demo"],'
            '"case_ids":["case-demo-42"]},'
            '"supervisor-token":{"principal_id":"sup-demo","tenant_id":"tenant-demo",'
            '"roles":["supervisor"],"subject_refs":["subject-demo"],'
            '"case_ids":["case-demo-42"]}}'
        )
    )
    case_api_base_url: str = ""
    case_api_token: str = ""
    indic_context_base_url: str = ""
    indic_context_token: str = ""

    def token_map_raw(self) -> dict[str, Any]:
        return json.loads(self.auth_tokens)
