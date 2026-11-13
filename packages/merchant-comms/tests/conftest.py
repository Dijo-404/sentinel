from __future__ import annotations

import pytest

from sentinel_merchant_comms.adapters.memory_store import (
    FixedClock,
    InMemoryDraftStore,
    SequentialIds,
)
from sentinel_merchant_comms.application.service import MerchantCommsService
from sentinel_merchant_comms.domain.types import Principal
from tests.stubs.case_api import ValidCaseApi
from tests.stubs.indic_context import ValidIndicContext


@pytest.fixture
def operator() -> Principal:
    return Principal(
        principal_id="op-demo",
        tenant_id="tenant-demo",
        roles=["operator"],
        subject_refs=["subject-demo"],
        case_ids=["case-demo-42"],
    )


@pytest.fixture
def service_factory():
    def _factory(*, case_api=None, indic=None, use_indic: bool = True):
        return MerchantCommsService(
            case_api=case_api or ValidCaseApi(),
            indic=(ValidIndicContext() if use_indic and indic is None else indic),
            store=InMemoryDraftStore(),
            clock=FixedClock("2026-11-13T19:30:00Z"),
            ids=SequentialIds(),
            default_channel="merchant-portal",
        )

    return _factory
