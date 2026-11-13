"""Composition root: wire config, ports and HTTP app."""

from __future__ import annotations

import os
from dataclasses import dataclass

from .adapters.auth import TokenAuthenticator, parse_token_map
from .adapters.clock import SystemClock
from .adapters.http_api import AppServices, create_app
from .adapters.peers_fixture import FixtureCaseApi, FixtureEvidence
from .adapters.peers_http import HttpCaseApi, HttpEvidence
from .adapters.storage_memory import MemoryDisputeStore
from .application.disputes import DisputeService
from .application.errors import ConfigurationError
from .domain.types import CONTRACT_VERSION


@dataclass(frozen=True)
class Settings:
    mode: str
    tokens: str
    case_api_base_url: str
    case_api_token: str
    evidence_base_url: str
    evidence_token: str
    default_deadline_seconds: int
    contract_version: str

    @classmethod
    def from_environ(cls, env: dict[str, str] | None = None) -> Settings:
        source = env if env is not None else os.environ
        mode = source.get("DISPUTES_MODE", "fixture")
        if mode not in {"fixture", "real-peers"}:
            raise ConfigurationError("DISPUTES_MODE must be fixture or real-peers")
        return cls(
            mode=mode,
            tokens=source.get("DISPUTES_TOKENS", ""),
            case_api_base_url=source.get("CASE_API_BASE_URL", ""),
            case_api_token=source.get("CASE_API_TOKEN", ""),
            evidence_base_url=source.get("EVIDENCE_BASE_URL", ""),
            evidence_token=source.get("EVIDENCE_TOKEN", ""),
            default_deadline_seconds=int(source.get("DISPUTES_DEFAULT_DEADLINE_SECONDS", "604800")),
            contract_version=source.get("DISPUTES_CONTRACT_VERSION", CONTRACT_VERSION),
        )


def build_app(
    settings: Settings | None = None,
    *,
    case_api=None,
    evidence=None,
    store=None,
    clock=None,
):
    settings = settings or Settings.from_environ()
    if settings.contract_version != CONTRACT_VERSION:
        raise ConfigurationError("Unsupported contract version")

    authenticator = TokenAuthenticator(parse_token_map(settings.tokens))
    if settings.mode == "fixture":
        case_peer = case_api or FixtureCaseApi()
        evidence_peer = evidence or FixtureEvidence()
        mode = "fixture"
    else:
        if not settings.case_api_base_url or not settings.case_api_token:
            raise ConfigurationError("CASE_API_BASE_URL and CASE_API_TOKEN required in real-peers")
        if not settings.evidence_base_url or not settings.evidence_token:
            raise ConfigurationError("EVIDENCE_BASE_URL and EVIDENCE_TOKEN required in real-peers")
        case_peer = case_api or HttpCaseApi(settings.case_api_base_url, settings.case_api_token)
        evidence_peer = evidence or HttpEvidence(
            settings.evidence_base_url, settings.evidence_token
        )
        mode = "real-peers"

    services = AppServices(
        authenticator=authenticator,
        disputes=DisputeService(
            case_api=case_peer,
            evidence=evidence_peer,
            store=store or MemoryDisputeStore(),
            clock=clock or SystemClock(),
            default_deadline_seconds=settings.default_deadline_seconds,
        ),
        mode=mode,
    )
    return create_app(services)
