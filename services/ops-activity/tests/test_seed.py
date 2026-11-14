"""Seed: sandbox-only rows; refuse missing URL / wrong tenant."""

from __future__ import annotations

import pytest

from sentinel_ops_activity.application.errors import ConfigurationError
from sentinel_ops_activity.seed import SEED_ACTIVITY_ID, SEED_TENANT_ID, seed_demo_activity


def test_seed_refuses_missing_database_url():
    with pytest.raises(ConfigurationError):
        seed_demo_activity("")


def test_seed_constants_are_sandbox():
    assert SEED_TENANT_ID == "tenant-demo"
    assert SEED_ACTIVITY_ID.startswith("act-seed-")
