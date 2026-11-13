from __future__ import annotations

from pathlib import Path

import pytest

from sentinel_finbench.bootstrap import load_bundled_dataset
from sentinel_finbench.domain.dataset import DatasetManifest


@pytest.fixture(scope="session")
def module_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def dataset() -> DatasetManifest:
    return load_bundled_dataset("indic-fin-v0.1.0")
