from __future__ import annotations

import json
from pathlib import Path

import pytest
from stubs import (
    ValidActionLedger,
    ValidEvidence,
    ValidIndicContext,
    ValidPolicy,
    ValidVerifier,
)

from sentinel_finharness import CaseManifest, RuntimeConfig

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def manifest() -> CaseManifest:
    raw = json.loads((ROOT / "fixtures" / "case-manifest.json").read_text(encoding="utf-8"))
    return CaseManifest.from_mapping(raw)


@pytest.fixture
def enabled_shadow(manifest: CaseManifest) -> RuntimeConfig:
    return RuntimeConfig.from_mapping(
        {
            "enabled": True,
            "execution_mode": "shadow",
            "financial_writes": False,
            "notifications": False,
            "allowed_workflows": [manifest.workflow_name],
            "allowed_tenants": ["sandbox"],
        }
    )


@pytest.fixture
def enabled_harness(manifest: CaseManifest) -> RuntimeConfig:
    return RuntimeConfig.from_mapping(
        {
            "enabled": True,
            "execution_mode": "harness",
            "financial_writes": True,
            "notifications": False,
            "allowed_workflows": [manifest.workflow_name],
            "allowed_tenants": ["sandbox"],
        }
    )


@pytest.fixture
def valid_peers():
    return {
        "evidence": ValidEvidence(),
        "policy": ValidPolicy(),
        "ledger": ValidActionLedger(),
        "verifier": ValidVerifier(),
        "indic_context": ValidIndicContext(),
    }
