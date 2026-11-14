"""Composition root: wire config, ports and HTTP app."""

from __future__ import annotations

import os
from dataclasses import dataclass

from .adapters.clock import SystemClock
from .adapters.delivery_sandbox import DEFAULT_ACCEPT_LINK_BASE, SandboxDeliveryAdapter
from .adapters.http import AppServices, create_app
from .adapters.seed import load_seed_users
from .adapters.storage_memory import MemoryIdentityStore
from .application.errors import ConfigurationError
from .application.service import IdentityService
from .domain.roles import CONTRACT_VERSION


@dataclass(frozen=True)
class Settings:
    mode: str
    contract_version: str
    database_url: str
    seed: bool
    accept_link_base: str

    @classmethod
    def from_environ(cls, env: dict[str, str] | None = None) -> Settings:
        source = env if env is not None else os.environ
        mode = source.get("IDENTITY_MODE", "fixture")
        if mode not in {"fixture", "real-peers"}:
            raise ConfigurationError("IDENTITY_MODE must be fixture or real-peers")
        return cls(
            mode=mode,
            contract_version=source.get("IDENTITY_CONTRACT_VERSION", CONTRACT_VERSION),
            database_url=source.get("IDENTITY_DATABASE_URL", ""),
            seed=source.get("IDENTITY_SEED", "1") not in {"0", "false", "False"},
            accept_link_base=source.get("IDENTITY_ACCEPT_LINK_BASE", DEFAULT_ACCEPT_LINK_BASE),
        )


def build_app(settings: Settings | None = None, *, store=None):
    settings = settings or Settings.from_environ()
    if settings.contract_version != CONTRACT_VERSION:
        raise ConfigurationError("Unsupported contract version")

    clock = SystemClock()
    if store is not None:
        identity_store = store
        mode = settings.mode
    elif settings.mode == "fixture" and not settings.database_url:
        identity_store = MemoryIdentityStore()
        mode = "fixture"
    elif settings.database_url:
        from .adapters.storage_postgres import PostgresIdentityStore, ensure_schema, make_engine

        engine = make_engine(settings.database_url)
        ensure_schema(engine)
        identity_store = PostgresIdentityStore(engine)
        mode = settings.mode
    else:
        # real-peers without DSN still uses memory for standalone checks; label mode.
        if settings.mode == "real-peers":
            raise ConfigurationError("IDENTITY_DATABASE_URL required in real-peers mode")
        identity_store = MemoryIdentityStore()
        mode = "fixture"

    if settings.seed:
        load_seed_users(identity_store, clock)

    delivery = SandboxDeliveryAdapter(
        identity_store, clock, accept_link_base=settings.accept_link_base
    )
    services = AppServices(
        identity=IdentityService(identity_store, clock, delivery=delivery),
        mode=mode,
    )
    return create_app(services)
