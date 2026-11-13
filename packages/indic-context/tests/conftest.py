from __future__ import annotations

import json
from pathlib import Path

import pytest

from sentinel_indic_context.adapters.auth import TokenMapAuth
from sentinel_indic_context.adapters.fake_sarvam import FakeSarvamAdapter
from sentinel_indic_context.adapters.http_api import create_app
from sentinel_indic_context.application.service import IndicContextService
from sentinel_indic_context.domain.types import ModelRequest, Principal

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


def load_fixture(name: str) -> tuple[ModelRequest, Principal]:
    payload = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    return ModelRequest.model_validate(payload["request"]), Principal.model_validate(
        payload["principal"]
    )


@pytest.fixture
def auth() -> TokenMapAuth:
    return TokenMapAuth(
        {
            "workflow-token": {
                "principal_id": "svc-workflow",
                "tenant_id": "tenant-demo",
                "roles": ["workflow"],
                "subject_refs": ["subject-demo"],
                "case_ids": ["case-demo-42"],
            }
        }
    )


@pytest.fixture
def service_factory():
    def _make(scenario: str = "proposal") -> IndicContextService:
        return IndicContextService(
            FakeSarvamAdapter(scenario=scenario),
            native_review_limit="human-review-required-for-refunds",
        )

    return _make


@pytest.fixture
def app(auth: TokenMapAuth, service_factory):
    return create_app(service=service_factory("proposal"), auth=auth, mode="fake")
