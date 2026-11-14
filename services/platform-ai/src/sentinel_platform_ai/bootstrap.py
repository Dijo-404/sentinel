"""Composition root: wire config, ports and HTTP app."""

from __future__ import annotations

import os
from dataclasses import dataclass

from .adapters.auth import TokenAuthenticator, parse_token_map
from .adapters.http import AppServices, create_app
from .adapters.storage_memory import MemoryPlatformAiStore
from .application.errors import ConfigurationError, PeerUnavailableError
from .application.ports import PlatformAiStore
from .application.service import PlatformAiService
from .domain.types import CONTRACT_VERSION


def _resolve_store(mode: str, store: PlatformAiStore | None, database_url: str) -> PlatformAiStore:
    if store is not None:
        return store
    if database_url.strip():
        from .adapters.storage_postgres import PostgresPlatformAiStore, build_engine

        pg = PostgresPlatformAiStore(build_engine(database_url))
        pg.migrate()
        return pg
    if mode == "real-peers":
        raise PeerUnavailableError(
            "real-peers requires PLATFORM_AI_DATABASE_URL or an injected durable store; "
            "MemoryPlatformAiStore defaults are not allowed across workers"
        )
    return MemoryPlatformAiStore()


@dataclass(frozen=True)
class Settings:
    mode: str
    tokens: str
    contract_version: str
    database_url: str = ""

    @classmethod
    def from_environ(cls, env: dict[str, str] | None = None) -> Settings:
        source = env if env is not None else os.environ
        mode = source.get("PLATFORM_AI_MODE", "fixture")
        if mode not in {"fixture", "real-peers"}:
            raise ConfigurationError("PLATFORM_AI_MODE must be fixture or real-peers")
        return cls(
            mode=mode,
            tokens=source.get("PLATFORM_AI_TOKENS", ""),
            contract_version=source.get("PLATFORM_AI_CONTRACT_VERSION", CONTRACT_VERSION),
            database_url=source.get("PLATFORM_AI_DATABASE_URL", ""),
        )


def build_app(settings: Settings | None = None, *, store: PlatformAiStore | None = None):
    settings = settings or Settings.from_environ()
    if settings.contract_version != CONTRACT_VERSION:
        raise ConfigurationError("Unsupported contract version")

    authenticator = TokenAuthenticator(parse_token_map(settings.tokens))
    platform_store = _resolve_store(settings.mode, store, settings.database_url)
    services = AppServices(
        authenticator=authenticator,
        service=PlatformAiService(platform_store),
        mode=settings.mode,
    )
    return create_app(services)
