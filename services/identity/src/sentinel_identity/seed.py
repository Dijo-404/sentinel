"""Sandbox seed: fixture principals + ≥1 notification into Postgres."""

from __future__ import annotations

from typing import Any

from .adapters.clock import SystemClock
from .adapters.seed import DEMO_PASSWORD, load_seed_users
from .adapters.storage_postgres import PostgresIdentityStore, ensure_schema, make_engine
from .application.errors import ConfigurationError
from .application.security import normalize_email

SANDBOX_TENANT = "tenant-demo"
SEED_CUSTOMER_EMAIL = "customer@example.test"
SEED_CUSTOMER_USER_ID = "11111111-1111-1111-1111-111111111101"
SEED_NOTIFICATION_ID = "11111111-1111-1111-1111-111111111301"
SEED_CUSTOMER_DISPLAY_NAME = "Demo Customer"
SEED_CUSTOMER_PREFERRED_LANGUAGE = "en"


def seed_demo_principals(database_url: str) -> dict[str, Any]:
    """Load seed_users.json into Postgres. Requires IDENTITY_DATABASE_URL.

    Challenge OTP fixtures stay test-only (IDENTITY_EXPOSE_SANDBOX_CODES /
    memory peek) — never written here.
    """
    if not (database_url or "").strip():
        raise ConfigurationError("IDENTITY_DATABASE_URL is required for seed")

    engine = make_engine(database_url)
    try:
        ensure_schema(engine)
        store = PostgresIdentityStore(engine)
        clock = SystemClock()
        loaded = load_seed_users(store, clock)
        customer = store.get_user_by_email(normalize_email(SEED_CUSTOMER_EMAIL))
        if customer is None:
            raise ConfigurationError(f"seed missing customer principal {SEED_CUSTOMER_EMAIL!r}")
        if customer.user_id != SEED_CUSTOMER_USER_ID:
            raise ConfigurationError(
                f"seed customer user_id want {SEED_CUSTOMER_USER_ID!r} got {customer.user_id!r}"
            )
        if not (customer.preferred_language or "").strip():
            raise ConfigurationError("seed customer preferred_language empty")
        notification = store.get_notification(SEED_NOTIFICATION_ID)
        if notification is None:
            raise ConfigurationError(f"seed missing notification {SEED_NOTIFICATION_ID!r}")
        if notification.user_id != SEED_CUSTOMER_USER_ID:
            raise ConfigurationError("seed notification user_id mismatch")
    finally:
        engine.dispose()

    return {
        "status": "PASS",
        "peer": "identity",
        "tenant_id": SANDBOX_TENANT,
        "customer_email": SEED_CUSTOMER_EMAIL,
        "notification_id": SEED_NOTIFICATION_ID,
        "rows": max(len(loaded), 1),
        "loaded": len(loaded),
        "demo_password_set": bool(DEMO_PASSWORD),
        "evidence_label": "synthetic-sandbox",
    }
