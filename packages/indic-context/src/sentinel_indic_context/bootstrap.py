"""Composition root: wire fake or live Sarvam ports."""

from __future__ import annotations

from fastapi import FastAPI

from sentinel_indic_context.adapters.auth import TokenMapAuth
from sentinel_indic_context.adapters.fake_sarvam import FakeSarvamAdapter
from sentinel_indic_context.adapters.http_api import create_app
from sentinel_indic_context.adapters.live_sarvam import LiveSarvamAdapter
from sentinel_indic_context.adapters.settings import Settings
from sentinel_indic_context.application.errors import ConfigurationError
from sentinel_indic_context.application.service import IndicContextService
from sentinel_indic_context.domain.types import CONTRACT_VERSION


def build_service(settings: Settings | None = None) -> IndicContextService:
    cfg = settings or Settings()
    if cfg.contract_version != CONTRACT_VERSION:
        raise ConfigurationError("contract version mismatch")
    if cfg.mode == "live":
        model = LiveSarvamAdapter(
            api_key=cfg.sarvam_api_key,
            base_url=cfg.sarvam_base_url,
            model_id=cfg.sarvam_model_id,
            timeout=cfg.sarvam_timeout_seconds,
        )
    else:
        model = FakeSarvamAdapter(
            scenario=cfg.fake_scenario,
            policy_version=cfg.policy_version,
        )
    return IndicContextService(model, native_review_limit=cfg.native_review_limit)


def build_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or Settings()
    service = build_service(cfg)
    auth = TokenMapAuth(cfg.token_map_raw())
    return create_app(service=service, auth=auth, mode=cfg.mode)
