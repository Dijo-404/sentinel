"""Composition root: wire HTTP report query app (evaluation.v1 authority)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from sentinel_evaluation.adapters.auth import TokenAuthenticator, parse_token_map
from sentinel_evaluation.adapters.http_api import AppServices, create_app
from sentinel_evaluation.adapters.storage_memory import MemoryReportStore
from sentinel_evaluation.application.errors import ConfigurationError, PeerUnavailableError
from sentinel_evaluation.application.ports import ReportStore
from sentinel_evaluation.application.reports import ReportQueryService
from sentinel_evaluation.domain.models import CONTRACT_VERSION


def _resolve_store(mode: str, store: ReportStore | None, database_url: str) -> ReportStore:
    if store is not None:
        return store
    if database_url.strip():
        from sentinel_evaluation.adapters.storage_postgres import PostgresReportStore, build_engine

        pg = PostgresReportStore(build_engine(database_url))
        pg.migrate()
        return pg
    if mode == "real-peers":
        raise PeerUnavailableError(
            "real-peers requires EVALUATION_DATABASE_URL or an injected durable store; "
            "MemoryReportStore defaults are not allowed across workers"
        )
    return MemoryReportStore()


@dataclass(frozen=True)
class Settings:
    mode: str
    tokens: str
    contract_version: str
    database_url: str = ""

    @classmethod
    def from_environ(cls, env: dict[str, str] | None = None) -> Settings:
        source = env if env is not None else os.environ
        mode = source.get("EVALUATION_MODE", "fixture")
        if mode not in {"fixture", "real-peers"}:
            raise ConfigurationError("EVALUATION_MODE must be fixture or real-peers")
        return cls(
            mode=mode,
            tokens=source.get("EVALUATION_TOKENS", ""),
            contract_version=source.get("EVALUATION_CONTRACT_VERSION", CONTRACT_VERSION),
            database_url=source.get("EVALUATION_DATABASE_URL", ""),
        )


def build_app(settings: Settings | None = None, *, store: ReportStore | None = None):
    settings = settings or Settings.from_environ()
    if settings.contract_version != CONTRACT_VERSION:
        raise ConfigurationError("Unsupported contract version")

    authenticator = TokenAuthenticator(parse_token_map(settings.tokens))
    report_store = _resolve_store(settings.mode, store, settings.database_url)
    services = AppServices(
        authenticator=authenticator,
        service=ReportQueryService(report_store),
        mode=settings.mode,
    )
    return create_app(services)
