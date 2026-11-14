"""Module-local settings."""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Canonical sandbox tokens + legacy aliases (see integration/core/docs/sandbox-matrix.md).
_DEFAULT_AUTH_TOKENS = (
    '{"tok-workflow":{"principal_id":"svc-workflow","tenant_id":"tenant-demo",'
    '"roles":["workflow"],"subject_refs":["subject-demo-42"],"case_ids":["case-demo-42"]},'
    '"tok-case-api":{"principal_id":"svc-case-api","tenant_id":"tenant-demo",'
    '"roles":["workflow"],"subject_refs":["subject-demo-42"],"case_ids":["case-demo-42"]},'
    '"tok-verifier":{"principal_id":"svc-verifier","tenant_id":"tenant-demo",'
    '"roles":["verifier"],"subject_refs":["subject-demo-42"],"case_ids":["case-demo-42"]},'
    '"tok-risk-officer":{"principal_id":"risk-officer-demo","tenant_id":"tenant-demo",'
    '"roles":["risk_officer"],"subject_refs":["subject-demo-42"],"case_ids":["case-demo-42"]},'
    '"workflow-token":{"principal_id":"svc-workflow","tenant_id":"tenant-demo",'
    '"roles":["workflow"],"subject_refs":["subject-demo"],"case_ids":["case-demo-42"]},'
    '"case-api-token":{"principal_id":"svc-case-api","tenant_id":"tenant-demo",'
    '"roles":["workflow"],"subject_refs":["subject-demo"],"case_ids":["case-demo-42"]},'
    '"verifier-token":{"principal_id":"svc-verifier","tenant_id":"tenant-demo",'
    '"roles":["verifier"],"subject_refs":["subject-demo"],"case_ids":["case-demo-42"]},'
    '"risk-token":{"principal_id":"risk-1","tenant_id":"tenant-demo",'
    '"roles":["risk_officer"],"subject_refs":["subject-demo"],"case_ids":["case-demo-42"]}}'
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WORKFLOW_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://workflow:workflow@127.0.0.1:5432/workflow"
    mode: Literal["fixture", "real-peers"] = "fixture"
    model_mode: Literal["fake", "http"] = "fake"
    fake_model_scenario: str = "proposal"
    investigation_budget: int = 8
    model_retry_budget: int = 2
    outbox_max_attempts: int = 10
    outbox_backoff_base_seconds: float = 0.0
    auth_tokens: str = Field(default=_DEFAULT_AUTH_TOKENS)
    peer_case_api_url: str = ""
    peer_evidence_url: str = ""
    peer_policy_url: str = ""
    peer_ledger_url: str = ""
    peer_verifier_url: str = ""
    peer_risk_url: str = ""
    peer_model_url: str = ""
    outbound_bearer: str = "tok-workflow"
    host: str = "127.0.0.1"
    port: int = 8088
    policy_version: str = "demo-policy-v1"

    def token_map_raw(self) -> dict[str, Any]:
        return json.loads(self.auth_tokens)
