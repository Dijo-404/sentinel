"""Seed CLI: refuse missing DSN; constants match fixtures/seed_users.json."""

from __future__ import annotations

import pytest

from sentinel_identity.application.errors import ConfigurationError
from sentinel_identity.seed import (
    SEED_CUSTOMER_EMAIL,
    SEED_CUSTOMER_PREFERRED_LANGUAGE,
    SEED_CUSTOMER_USER_ID,
    SEED_NOTIFICATION_ID,
    seed_demo_principals,
)


def test_seed_markers_match_fixture_json() -> None:
    assert SEED_CUSTOMER_EMAIL == "customer@example.test"
    assert SEED_CUSTOMER_USER_ID == "11111111-1111-1111-1111-111111111101"
    assert SEED_NOTIFICATION_ID == "11111111-1111-1111-1111-111111111301"
    assert SEED_CUSTOMER_PREFERRED_LANGUAGE == "en"


def test_seed_refuses_missing_database_url() -> None:
    with pytest.raises(ConfigurationError, match="IDENTITY_DATABASE_URL"):
        seed_demo_principals("")
