"""Composition root: wire config, ports and HTTP app."""

from __future__ import annotations

import os
from dataclasses import dataclass

from .adapters.auth import TokenAuthenticator, parse_token_map
from .adapters.case_api_http import HttpCaseApi
from .adapters.case_api_stub import StubCaseApi
from .adapters.clock import SystemClock
from .adapters.http_api import AppServices, create_app
from .adapters.identity_http import HttpIdentityMemberships
from .adapters.identity_stub import StubIdentityMemberships
from .adapters.storage_memory import MemoryStaffStore
from .application.errors import ConfigurationError
from .application.ports import CaseApiPort, IdentityMembershipPort
from .application.staff import StaffService
from .domain.types import CONTRACT_VERSION


@dataclass(frozen=True)
class Settings:
    mode: str
    tokens: str
    case_api_base_url: str
    case_api_token: str
    identity_base_url: str
    identity_token: str
    contract_version: str

    @classmethod
    def from_environ(cls, env: dict[str, str] | None = None) -> Settings:
        source = env if env is not None else os.environ
        mode = source.get("MERCHANT_TEAMS_MODE", "fixture")
        if mode not in {"fixture", "real-peers"}:
            raise ConfigurationError("MERCHANT_TEAMS_MODE must be fixture or real-peers")
        return cls(
            mode=mode,
            tokens=source.get("MERCHANT_TEAMS_TOKENS", ""),
            case_api_base_url=source.get("CASE_API_BASE_URL", ""),
            case_api_token=source.get("CASE_API_TOKEN", ""),
            identity_base_url=source.get("IDENTITY_BASE_URL", ""),
            identity_token=source.get("IDENTITY_TOKEN", ""),
            contract_version=source.get("MERCHANT_TEAMS_CONTRACT_VERSION", CONTRACT_VERSION),
        )


def build_app(
    settings: Settings | None = None,
    *,
    store: MemoryStaffStore | None = None,
    cases: CaseApiPort | None = None,
    identity: IdentityMembershipPort | None = None,
):
    settings = settings or Settings.from_environ()
    if settings.contract_version != CONTRACT_VERSION:
        raise ConfigurationError("Unsupported contract version")

    authenticator = TokenAuthenticator(parse_token_map(settings.tokens))
    if settings.mode == "fixture":
        case_port = cases if cases is not None else StubCaseApi(mode="valid")
        identity_port = identity if identity is not None else StubIdentityMemberships(mode="valid")
        mode = "fixture"
    else:
        if cases is not None:
            case_port = cases
        else:
            case_port = HttpCaseApi(
                base_url=settings.case_api_base_url,
                token=settings.case_api_token,
            )
        if identity is not None:
            identity_port = identity
        elif settings.identity_base_url.strip():
            identity_port = HttpIdentityMemberships(
                base_url=settings.identity_base_url,
                token=settings.identity_token,
            )
        else:
            identity_port = None
        mode = "real-peers"

    staff_store = store if store is not None else MemoryStaffStore()
    services = AppServices(
        authenticator=authenticator,
        staff=StaffService(staff_store, case_port, SystemClock(), identity_port),
        mode=mode,
    )
    return create_app(services)
