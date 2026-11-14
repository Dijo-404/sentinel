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
    token_map_path: str = "fixtures/auth_tokens.json"
    service_token: str = "tok-case-api"
    host: str = "127.0.0.1"

    def token_path(self, base: Path) -> Path:
        path = Path(self.token_map_path)
        return path if path.is_absolute() else base / path
