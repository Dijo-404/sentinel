"""Seed: sandbox-only rows; refuse missing URL."""

from __future__ import annotations

import pytest

from sentinel_observability.application.errors import ConfigurationError
from sentinel_observability.seed import SEED_SIGNAL_ID, SEED_TENANT_ID, seed_demo_signal


def test_seed_refuses_missing_database_url():
    with pytest.raises(ConfigurationError):
        seed_demo_signal("")


def test_seed_constants_are_sandbox():
    assert SEED_TENANT_ID == "tenant-demo"
    assert SEED_SIGNAL_ID.startswith("sig-seed-")
