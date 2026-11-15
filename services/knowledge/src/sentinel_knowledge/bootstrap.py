"""Composition root: wire config, ports and HTTP app."""

from __future__ import annotations

import os
from dataclasses import dataclass

from .adapters.auth import TokenAuthenticator, parse_token_map
from .adapters.embedder_fastembed import DEFAULT_MODEL as DEFAULT_EMBEDDING_MODEL
from .adapters.embedder_fastembed import FastEmbedEmbedder
from .adapters.http import AppServices, create_app
from .adapters.storage_memory import MemoryArticleStore
from .application.errors import ConfigurationError, PeerUnavailableError
from .application.service import KnowledgeService
from .domain.types import CONTRACT_VERSION


@dataclass(frozen=True)
class Settings:
    mode: str
    tokens: str
    database_url: str
    contract_version: str
    embedding_model: str = DEFAULT_EMBEDDING_MODEL
    embedding_cache_dir: str = ""

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
            embedding_model=source.get("KNOWLEDGE_EMBEDDING_MODEL") or DEFAULT_EMBEDDING_MODEL,
            embedding_cache_dir=source.get("KNOWLEDGE_EMBEDDING_CACHE_DIR", ""),
        )


def build_embedder(settings: Settings) -> FastEmbedEmbedder:
    return FastEmbedEmbedder(settings.embedding_model, settings.embedding_cache_dir or None)


def build_postgres_store(settings: Settings, embedder=None, *, reset_dimension: bool = False):
    """Migrated pgvector store. Raises (fail closed) if DB, pgvector or embedder is missing."""
    if not settings.database_url.strip():
        raise ConfigurationError("KNOWLEDGE_DATABASE_URL is required")
    from .adapters.storage_postgres import PostgresArticleStore, build_engine

    store = PostgresArticleStore(
        build_engine(settings.database_url), embedder or build_embedder(settings)
    )
    store.migrate(reset_dimension=reset_dimension)
    return store


def _resolve_store(settings: Settings, store, embedder):
    if store is not None:
        return store
    if settings.database_url:
        pg_store = build_postgres_store(settings, embedder)
        pg_store.reindex()  # embed rows written before pgvector or by another model
        return pg_store
    if settings.mode == "real-peers":
        raise PeerUnavailableError(
            "real-peers requires KNOWLEDGE_DATABASE_URL or an injected durable store; "
            "MemoryArticleStore defaults are not allowed across workers"
        )
    return MemoryArticleStore()


def build_app(settings: Settings | None = None, *, store=None, embedder=None):
    settings = settings or Settings.from_environ()
    if settings.contract_version != CONTRACT_VERSION:
        raise ConfigurationError("Unsupported contract version")

    authenticator = TokenAuthenticator(parse_token_map(settings.tokens))
    article_store = _resolve_store(settings, store, embedder)
    services = AppServices(
        authenticator=authenticator,
        knowledge=KnowledgeService(store=article_store),
        mode=settings.mode,
        search=getattr(article_store, "search_mode", "unknown"),
    )
    return create_app(services)
