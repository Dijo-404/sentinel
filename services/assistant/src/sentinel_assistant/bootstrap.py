"""Composition root: wire config, ports and HTTP app."""

from __future__ import annotations

import os
from dataclasses import dataclass

from .adapters.auth import TokenAuthenticator, parse_token_map
from .adapters.clock import SystemClock
from .adapters.http_api import AppServices, create_app
from .adapters.storage_memory import MemoryAssistantStore
from .application.errors import ConfigurationError, PeerUnavailableError
from .application.service import AssistantService
from .domain.types import CONTRACT_VERSION


def _resolve_store(mode: str, store, database_url: str):
    if store is not None:
        return store
    if database_url:
        from .adapters.storage_postgres import PostgresAssistantStore, build_engine

        engine = build_engine(database_url)
        pg_store = PostgresAssistantStore(engine)
        pg_store.migrate()
        return pg_store
    if mode == "real-peers":
        raise PeerUnavailableError(
            "real-peers requires ASSISTANT_DATABASE_URL or an injected durable store; "
            "MemoryAssistantStore defaults are not allowed across workers"
        )
    return MemoryAssistantStore()


@dataclass(frozen=True)
class Settings:
    mode: str
    tokens: str
    database_url: str
    contract_version: str

    @classmethod
    def from_environ(cls, env: dict[str, str] | None = None) -> Settings:
        source = env if env is not None else os.environ
        mode = source.get("ASSISTANT_MODE", "fixture")
        if mode not in {"fixture", "real-peers"}:
            raise ConfigurationError("ASSISTANT_MODE must be fixture or real-peers")
        return cls(
            mode=mode,
            tokens=source.get("ASSISTANT_TOKENS", ""),
            database_url=source.get("ASSISTANT_DATABASE_URL", ""),
            contract_version=source.get("ASSISTANT_CONTRACT_VERSION", CONTRACT_VERSION),
        )


def build_app(
    settings: Settings | None = None,
    *,
    store=None,
    clock=None,
):
    settings = settings or Settings.from_environ()
    if settings.contract_version != CONTRACT_VERSION:
        raise ConfigurationError("Unsupported contract version")

    authenticator = TokenAuthenticator(parse_token_map(settings.tokens))
    services = AppServices(
        authenticator=authenticator,
        assistant=AssistantService(
            store=_resolve_store(settings.mode, store, settings.database_url),
            clock=clock or SystemClock(),
        ),
        mode=settings.mode,
    )
    return create_app(services)
