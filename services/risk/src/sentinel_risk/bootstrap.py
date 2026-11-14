"""Composition root: wire config, ports and HTTP app."""

from __future__ import annotations

import os
from dataclasses import dataclass

from .adapters.auth import TokenAuthenticator, parse_token_map
from .adapters.clock import SystemClock
from .adapters.http_api import AppServices, create_app
from .adapters.peers_fixture import FixtureCaseApi, FixtureWorkflow
from .adapters.peers_http import HttpCaseApi, HttpWorkflow
from .adapters.storage_memory import MemoryRiskStore
from .application.errors import ConfigurationError, PeerUnavailableError
from .application.risk import RiskService
from .domain.types import CONTRACT_VERSION


def _resolve_store(mode: str, store, database_url: str):
    if store is not None:
        return store
    if database_url:
        from .adapters.storage_postgres import PostgresRiskStore, build_engine

        engine = build_engine(database_url)
        pg_store = PostgresRiskStore(engine)
        pg_store.migrate()
        return pg_store
    if mode == "real-peers":
        raise PeerUnavailableError(
            "real-peers requires RISK_DATABASE_URL or an injected durable store; "
            "MemoryRiskStore defaults are not allowed across workers"
        )
    return MemoryRiskStore()


@dataclass(frozen=True)
class Settings:
    mode: str
    tokens: str
    case_api_base_url: str
    case_api_token: str
    workflow_base_url: str
    workflow_token: str
    database_url: str
    contract_version: str

    @classmethod
    def from_environ(cls, env: dict[str, str] | None = None) -> Settings:
        source = env if env is not None else os.environ
        mode = source.get("RISK_MODE", "fixture")
        if mode not in {"fixture", "real-peers"}:
            raise ConfigurationError("RISK_MODE must be fixture or real-peers")
        return cls(
            mode=mode,
            tokens=source.get("RISK_TOKENS", ""),
            case_api_base_url=source.get("CASE_API_BASE_URL", ""),
            case_api_token=source.get("CASE_API_TOKEN", ""),
            workflow_base_url=source.get("WORKFLOW_BASE_URL", ""),
            workflow_token=source.get("WORKFLOW_TOKEN", ""),
            database_url=source.get("RISK_DATABASE_URL", ""),
            contract_version=source.get("RISK_CONTRACT_VERSION", CONTRACT_VERSION),
        )


def build_app(
    settings: Settings | None = None,
    *,
    case_api=None,
    workflow=None,
    store=None,
    clock=None,
):
    settings = settings or Settings.from_environ()
    if settings.contract_version != CONTRACT_VERSION:
        raise ConfigurationError("Unsupported contract version")

    authenticator = TokenAuthenticator(parse_token_map(settings.tokens))
    if settings.mode == "fixture":
        case_peer = case_api or FixtureCaseApi()
        workflow_peer = workflow or FixtureWorkflow()
        mode = "fixture"
    else:
        if not settings.case_api_base_url or not settings.case_api_token:
            raise ConfigurationError("CASE_API_BASE_URL and CASE_API_TOKEN required in real-peers")
        if not settings.workflow_base_url or not settings.workflow_token:
            raise ConfigurationError("WORKFLOW_BASE_URL and WORKFLOW_TOKEN required in real-peers")
        case_peer = case_api or HttpCaseApi(settings.case_api_base_url, settings.case_api_token)
        workflow_peer = workflow or HttpWorkflow(
            settings.workflow_base_url, settings.workflow_token
        )
        mode = "real-peers"

    services = AppServices(
        authenticator=authenticator,
        risk=RiskService(
            case_api=case_peer,
            workflow=workflow_peer,
            store=_resolve_store(mode, store, settings.database_url),
            clock=clock or SystemClock(),
        ),
        mode=mode,
    )
    return create_app(services)
