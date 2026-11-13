"""Composition root: wire fixture peers or real-peer HTTP adapters."""

from __future__ import annotations

from fastapi import FastAPI

from sentinel_merchant_comms.adapters.auth import TokenMapAuth
from sentinel_merchant_comms.adapters.case_api_http import CaseApiHttpClient
from sentinel_merchant_comms.adapters.fixture_peers import FixtureCaseApi, FixtureIndicContext
from sentinel_merchant_comms.adapters.http_api import create_app
from sentinel_merchant_comms.adapters.indic_context_http import IndicContextHttpClient
from sentinel_merchant_comms.adapters.memory_store import (
    FixedClock,
    InMemoryDraftStore,
    SequentialIds,
    SystemClock,
)
from sentinel_merchant_comms.adapters.settings import Settings
from sentinel_merchant_comms.application.errors import ConfigurationError
from sentinel_merchant_comms.application.service import MerchantCommsService
from sentinel_merchant_comms.domain.types import CONTRACT_VERSION


def build_service(
    settings: Settings | None = None,
    *,
    case_api=None,
    indic=None,
    store: InMemoryDraftStore | None = None,
    clock=None,
    ids=None,
    use_indic: bool | None = None,
) -> MerchantCommsService:
    cfg = settings or Settings()
    if cfg.contract_version != CONTRACT_VERSION:
        raise ConfigurationError("contract version mismatch")

    if case_api is None:
        if cfg.mode == "real-peers":
            if not cfg.case_api_base_url:
                raise ConfigurationError("CASE_API_BASE_URL required in real-peers mode")
            case_api = CaseApiHttpClient(
                base_url=cfg.case_api_base_url,
                token=cfg.case_api_token,
            )
        else:
            case_api = FixtureCaseApi()

    if indic is None and use_indic is not False:
        if cfg.indic_context_base_url:
            indic = IndicContextHttpClient(
                base_url=cfg.indic_context_base_url,
                token=cfg.indic_context_token,
            )
        elif cfg.mode == "fixture":
            indic = FixtureIndicContext()
        else:
            indic = None
    elif use_indic is False:
        indic = None

    return MerchantCommsService(
        case_api=case_api,
        indic=indic,
        store=store or InMemoryDraftStore(),
        clock=clock or (FixedClock() if cfg.mode == "fixture" else SystemClock()),
        ids=ids or SequentialIds(),
        default_channel=cfg.default_channel,
    )


def build_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or Settings()
    service = build_service(cfg)
    auth = TokenMapAuth(cfg.token_map_raw())
    return create_app(service=service, auth=auth, mode=cfg.mode)
