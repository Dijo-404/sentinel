"""Composition root: wire config, ports and HTTP app."""

from __future__ import annotations

import os
from dataclasses import dataclass

from sqlalchemy import create_engine

from .adapters.auth import TokenAuthenticator, parse_token_map
from .adapters.clock import SystemClock
from .adapters.http_api import AppServices, create_app
from .adapters.provider_http import HttpPaymentProvider
from .adapters.provider_stub import CaseSelectingStub
from .adapters.storage_memory import MemoryEvidenceStore
from .adapters.storage_postgres import PostgresEvidenceStore
from .application.collect import CollectEvidence, ListEvidence
from .application.errors import ConfigurationError
from .domain.types import CONTRACT_VERSION


@dataclass(frozen=True)
class Settings:
    mode: str
    database_url: str | None
    schema: str
    tokens: str
    provider_base_url: str
    provider_token: str
    ttl_seconds: int
    contract_version: str

    @classmethod
    def from_environ(cls, env: dict[str, str] | None = None) -> Settings:
        source = env if env is not None else os.environ
        mode = source.get("EVIDENCE_MODE", "fixture")
        if mode not in {"fixture", "real-peers"}:
            raise ConfigurationError("EVIDENCE_MODE must be fixture or real-peers")
        return cls(
            mode=mode,
            database_url=source.get("DATABASE_URL"),
            schema=source.get("EVIDENCE_SCHEMA", "evidence"),
            tokens=source.get("EVIDENCE_TOKENS", ""),
            provider_base_url=source.get("PAYMENT_PROVIDER_BASE_URL", ""),
            provider_token=source.get("PAYMENT_PROVIDER_TOKEN", ""),
            ttl_seconds=int(source.get("EVIDENCE_TTL_SECONDS", "3600")),
            contract_version=source.get("EVIDENCE_CONTRACT_VERSION", CONTRACT_VERSION),
        )


def build_app(settings: Settings | None = None, *, use_memory_store: bool = False):
    settings = settings or Settings.from_environ()
    if settings.contract_version != CONTRACT_VERSION:
        raise ConfigurationError("Unsupported contract version")

    authenticator = TokenAuthenticator(parse_token_map(settings.tokens))
    if settings.mode == "fixture":
        provider = CaseSelectingStub()
        mode = "fixture"
    else:
        provider = HttpPaymentProvider(
            base_url=settings.provider_base_url,
            token=settings.provider_token,
            ttl_seconds=settings.ttl_seconds,
        )
        mode = "real-peers"

    if use_memory_store or not settings.database_url:
        store = MemoryEvidenceStore()
    else:
        engine = create_engine(settings.database_url, hide_parameters=True)
        store = PostgresEvidenceStore(engine, schema=settings.schema)
        store.migrate()

    clock = SystemClock()
    services = AppServices(
        authenticator=authenticator,
        collect=CollectEvidence(provider, store, clock),
        list_evidence=ListEvidence(store),
        mode=mode,
    )
    return create_app(services)
