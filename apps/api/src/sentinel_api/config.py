"""Module-local settings."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SENTINEL_API_", extra="ignore")

    mode: str = Field(default="fixture")
    database_url: str = Field(
        default="postgresql+psycopg://sentinel:sentinel@127.0.0.1:5432/sentinel_api"
    )
    workflow_base_url: str = ""
    evidence_base_url: str = ""
    ledger_base_url: str = ""
    verifier_base_url: str = ""
    identity_base_url: str = ""
    identity_customer_subject_bindings: dict[str, dict[str, list[str]]] = Field(
        default_factory=dict
    )
    token_map_path: str = "fixtures/auth_tokens.json"
    identity_sessions_path: str = "fixtures/identity_sessions.json"
    service_token: str = "tok-case-api"
    host: str = "127.0.0.1"
    # Workflow outbox: bounded retry of transient peer rejections (409/422/429).
    workflow_retry_max_attempts: int = Field(default=5, ge=1)
    workflow_retry_base_seconds: float = Field(default=2.0, gt=0)
    workflow_retry_max_seconds: float = Field(default=300.0, gt=0)

    def token_path(self, base: Path) -> Path:
        path = Path(self.token_map_path)
        return path if path.is_absolute() else base / path

    def identity_path(self, base: Path) -> Path:
        path = Path(self.identity_sessions_path)
        return path if path.is_absolute() else base / path
