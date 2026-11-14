"""Composition root: wire config, ports and HTTP app."""

from __future__ import annotations

import os
from dataclasses import dataclass

from .adapters.auth import TokenAuthenticator, parse_token_map
from .adapters.case_http import HttpCaseApi
from .adapters.evidence_http import HttpEvidence
from .adapters.fixture_peers import FixtureCaseApi, FixtureEvidence
from .adapters.http_api import AppServices, create_app
from .application.errors import ConfigurationError
from .application.get_metrics import GetMerchantMetrics
from .domain.types import CONTRACT_VERSION


@dataclass(frozen=True)
class Settings:
    mode: str
    tokens: str
    case_api_base_url: str
    case_api_token: str
    evidence_base_url: str
    evidence_token: str
    contract_version: str
    database_url: str = ""

    @classmethod
    def from_environ(cls, env: dict[str, str] | None = None) -> Settings:
        source = env if env is not None else os.environ
        mode = source.get("MERCHANT_ANALYTICS_MODE", "fixture")
        if mode not in {"fixture", "real-peers"}:
            raise ConfigurationError("MERCHANT_ANALYTICS_MODE must be fixture or real-peers")
        return cls(
            mode=mode,
            tokens=source.get("MERCHANT_ANALYTICS_TOKENS", ""),
            case_api_base_url=source.get("CASE_API_BASE_URL", ""),
            case_api_token=source.get("CASE_API_TOKEN", ""),
            evidence_base_url=source.get("EVIDENCE_BASE_URL", ""),
            evidence_token=source.get("EVIDENCE_TOKEN", ""),
            database_url=source.get("MERCHANT_ANALYTICS_DATABASE_URL", ""),
            contract_version=source.get("MERCHANT_ANALYTICS_CONTRACT_VERSION", CONTRACT_VERSION),
        )


def _resolve_snapshots(database_url: str):
    if not database_url:
        return None
    from .adapters.postgres_snapshots import PostgresMetricsSnapshotStore, build_engine

    store = PostgresMetricsSnapshotStore(build_engine(database_url))
    store.migrate()
    return store


def build_app(
    settings: Settings | None = None,
    *,
    case_api: object | None = None,
    evidence: object | None = None,
    snapshots: object | None = None,
):
    settings = settings or Settings.from_environ()
    if settings.contract_version != CONTRACT_VERSION:
        raise ConfigurationError("Unsupported contract version")

    authenticator = TokenAuthenticator(parse_token_map(settings.tokens))
    store = snapshots if snapshots is not None else _resolve_snapshots(settings.database_url)

    if case_api is not None and evidence is not None:
        cases_port = case_api
        evidence_port = evidence
        mode = settings.mode
        require_snapshot = store is not None and settings.mode == "real-peers"
    elif settings.mode == "fixture":
        cases_port = FixtureCaseApi(behavior="valid")
        evidence_port = FixtureEvidence(behavior="valid")
        mode = "fixture"
        require_snapshot = False
    elif store is not None:
        # real-peers with DB: serve metrics from snapshots only (no live invent).
        cases_port = None
        evidence_port = None
        mode = "real-peers"
        require_snapshot = True
    else:
        cases_port = HttpCaseApi(
            base_url=settings.case_api_base_url,
            token=settings.case_api_token,
        )
        evidence_port = HttpEvidence(
            base_url=settings.evidence_base_url,
            token=settings.evidence_token,
        )
        mode = "real-peers"
        require_snapshot = False

    services = AppServices(
        authenticator=authenticator,
        get_metrics=GetMerchantMetrics(
            cases_port,  # type: ignore[arg-type]
            evidence_port,  # type: ignore[arg-type]
            snapshots=store,  # type: ignore[arg-type]
            require_snapshot=require_snapshot,
        ),
        mode=mode,
    )
    return create_app(services)
