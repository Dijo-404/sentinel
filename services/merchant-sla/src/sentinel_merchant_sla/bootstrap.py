"""Composition root: config, tokens, clock, case peer, app."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from sentinel_merchant_sla.adapters.auth import TokenMap
from sentinel_merchant_sla.adapters.case_api_fixture import FixtureCaseApi
from sentinel_merchant_sla.adapters.case_api_http import HttpCaseApi
from sentinel_merchant_sla.adapters.clock import SystemClock
from sentinel_merchant_sla.adapters.http_api import create_app
from sentinel_merchant_sla.adapters.memory_store import MemorySlaStore
from sentinel_merchant_sla.adapters.sqlite_store import SqliteSlaStore
from sentinel_merchant_sla.application.errors import ConfigurationError, PeerUnavailableError
from sentinel_merchant_sla.application.ports import CaseApiPort, Clock, SlaStore
from sentinel_merchant_sla.application.service import MerchantSlaService


def _resolve_store(mode: str, store: SlaStore | None, database_url: str):
    if store is not None:
        return store
    if database_url:
        return SqliteSlaStore.from_url(database_url)
    if mode == "real-peers":
        raise PeerUnavailableError(
            "real-peers requires MERCHANT_SLA_DATABASE_URL or an injected durable store; "
            "MemorySlaStore defaults are not allowed across workers"
        )
    return MemorySlaStore()


MODULE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PRINCIPALS = MODULE_ROOT / "contracts" / "principals.json"


@dataclass(frozen=True)
class Settings:
    mode: str
    principals_path: Path
    case_api_base_url: str
    case_api_token: str
    database_url: str = ""


def load_settings(
    *,
    mode: str | None = None,
    principals_path: Path | None = None,
) -> Settings:
    path = principals_path or Path(
        os.environ.get("MERCHANT_SLA_PRINCIPALS_PATH", str(DEFAULT_PRINCIPALS))
    )
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    return Settings(
        mode=mode or os.environ.get("MERCHANT_SLA_MODE", "fixture"),
        principals_path=path,
        case_api_base_url=os.environ.get("MERCHANT_SLA_CASE_API_BASE_URL", ""),
        case_api_token=os.environ.get("MERCHANT_SLA_CASE_API_TOKEN", ""),
        database_url=os.environ.get("MERCHANT_SLA_DATABASE_URL", ""),
    )


def build_case_api(settings: Settings, *, case_api: CaseApiPort | None = None) -> CaseApiPort:
    if case_api is not None:
        return case_api
    if settings.mode == "fixture":
        return FixtureCaseApi(behavior="valid")
    if settings.mode == "real-peers":
        if not settings.case_api_base_url or not settings.case_api_token:
            raise ConfigurationError(
                "real-peers mode requires MERCHANT_SLA_CASE_API_BASE_URL and "
                "MERCHANT_SLA_CASE_API_TOKEN; fixture fallback is disabled"
            )
        return HttpCaseApi(
            base_url=settings.case_api_base_url,
            token=settings.case_api_token,
        )
    raise ConfigurationError(f"unknown mode: {settings.mode}")


def build_app(
    *,
    settings: Settings | None = None,
    clock: Clock | None = None,
    store: SlaStore | None = None,
    case_api: CaseApiPort | None = None,
):
    cfg = settings or load_settings()
    tokens = TokenMap.from_path(cfg.principals_path)
    peer = build_case_api(cfg, case_api=case_api)
    service = MerchantSlaService(
        store=_resolve_store(cfg.mode, store, cfg.database_url),
        clock=clock or SystemClock(),
        case_api=peer,
    )
    return create_app(service=service, tokens=tokens, mode=cfg.mode)
