"""Composition root: wire config, ports and HTTP app."""

from __future__ import annotations

import os
from dataclasses import dataclass

from .adapters.auth import TokenAuthenticator, parse_token_map
from .adapters.http import AppServices, create_app
from .adapters.storage_memory import MemoryArticleStore
from .application.errors import ConfigurationError, PeerUnavailableError
from .application.service import KnowledgeService
from .domain.types import CONTRACT_VERSION


def _resolve_store(mode: str, store, database_url: str):
    if store is not None:
        return store
    if database_url:
        from .adapters.storage_postgres import PostgresArticleStore, build_engine

        engine = build_engine(database_url)
        pg_store = PostgresArticleStore(engine)
        pg_store.migrate()
        return pg_store
    if mode == "real-peers":
        raise PeerUnavailableError(
            "real-peers requires KNOWLEDGE_DATABASE_URL or an injected durable store; "
            "MemoryArticleStore defaults are not allowed across workers"
        )
    return MemoryArticleStore()


@dataclass(frozen=True)
class Settings:
    mode: str
    tokens: str
    database_url: str
    contract_version: str

    @classmethod
    def from_environ(cls, env: dict[str, str] | None = None) -> Settings:
        source = env if env is not None else os.environ
        mode = source.get("KNOWLEDGE_MODE", "fixture")
        if mode not in {"fixture", "real-peers"}:
            raise ConfigurationError("KNOWLEDGE_MODE must be fixture or real-peers")
        return cls(
            mode=mode,
            tokens=source.get("KNOWLEDGE_TOKENS", ""),
            database_url=source.get("KNOWLEDGE_DATABASE_URL", ""),
            contract_version=source.get("KNOWLEDGE_CONTRACT_VERSION", CONTRACT_VERSION),
        )


def build_app(settings: Settings | None = None, *, store=None):
    settings = settings or Settings.from_environ()
    if settings.contract_version != CONTRACT_VERSION:
        raise ConfigurationError("Unsupported contract version")

    authenticator = TokenAuthenticator(parse_token_map(settings.tokens))
    article_store = _resolve_store(settings.mode, store, settings.database_url)
    services = AppServices(
        authenticator=authenticator,
        knowledge=KnowledgeService(store=article_store),
        mode=settings.mode,
    )
    return create_app(services)
