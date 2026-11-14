"""Seed requires ASSISTANT_DATABASE_URL and writes sandbox thread + message."""

from __future__ import annotations

import pytest

from sentinel_assistant.application.errors import ConfigurationError
from sentinel_assistant.seed import seed_demo_threads


def test_seed_requires_database_url():
    with pytest.raises(ConfigurationError) as exc:
        seed_demo_threads("")
    assert "ASSISTANT_DATABASE_URL" in exc.value.message
