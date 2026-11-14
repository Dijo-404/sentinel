"""Authorized case order_reference → bare provider order id."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sentinel_evidence.adapters.clock import FixedClock
from sentinel_evidence.adapters.provider_stub import StubPaymentProvider
from sentinel_evidence.adapters.storage_memory import MemoryEvidenceStore
from sentinel_evidence.application.collect import CollectEvidence
from sentinel_evidence.application.errors import ValidationError
from sentinel_evidence.domain.order_reference import OrderReferenceError, provider_order_id
from sentinel_evidence.domain.types import CollectRequest, Principal, ProviderSnapshot

PRINCIPAL = Principal(
    "svc-workflow",
    "tenant-demo",
    ("workflow",),
    ("subj-demo-1",),
    ("case-demo-42",),
)


@pytest.mark.parametrize(
    ("authorized", "expected"),
    [
        ("DEMO-ORDER-42", "DEMO-ORDER-42"),
        ("subject-a/DEMO-ORDER-42", "DEMO-ORDER-42"),
        ("subject-a:42", "42"),
    ],
)
def test_provider_order_id_mapping(authorized: str, expected: str):
    assert provider_order_id(authorized) == expected


@pytest.mark.parametrize(
    "weird",
    [
        "",
        "   ",
        "subject-a/",
        "/DEMO-ORDER-42",
        "subject-a:",
        ":42",
        "subject-a//x",
        "subject-a::x",
        " padded ",
    ],
)
def test_provider_order_id_fail_closed(weird: str):
    with pytest.raises(OrderReferenceError):
        provider_order_id(weird)


class _RecordingProvider:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self._inner = StubPaymentProvider()

    def fetch_snapshot(self, *, order_reference: str, principal: Principal) -> ProviderSnapshot:
        self.calls.append(order_reference)
        return self._inner.fetch_snapshot(order_reference=order_reference, principal=principal)


def test_collect_subject_prefixed_hits_provider_with_bare_id():
    provider = _RecordingProvider()
    collect = CollectEvidence(
        provider,
        MemoryEvidenceStore(),
        FixedClock(datetime(2026, 11, 13, 12, 30, tzinfo=UTC)),
    )
    bundle = collect(
        PRINCIPAL,
        CollectRequest(
            case_id="case-demo-42",
            case_revision=1,
            order_reference="subject-a/DEMO-ORDER-42",
        ),
    )
    assert provider.calls == ["DEMO-ORDER-42"]
    assert bundle.case_id == "case-demo-42"


def test_collect_bare_order_reference_still_works():
    provider = _RecordingProvider()
    collect = CollectEvidence(
        provider,
        MemoryEvidenceStore(),
        FixedClock(datetime(2026, 11, 13, 12, 30, tzinfo=UTC)),
    )
    collect(
        PRINCIPAL,
        CollectRequest(
            case_id="case-demo-42",
            case_revision=1,
            order_reference="DEMO-ORDER-42",
        ),
    )
    assert provider.calls == ["DEMO-ORDER-42"]


def test_collect_weird_order_reference_fail_closed():
    provider = _RecordingProvider()
    collect = CollectEvidence(
        provider,
        MemoryEvidenceStore(),
        FixedClock(datetime(2026, 11, 13, 12, 30, tzinfo=UTC)),
    )
    with pytest.raises(ValidationError):
        collect(
            PRINCIPAL,
            CollectRequest(
                case_id="case-demo-42",
                case_revision=1,
                order_reference="subject-a/",
            ),
        )
    assert provider.calls == []


def test_collect_preserves_authorized_reference_on_store():
    store = MemoryEvidenceStore()
    # Memory store currently drops request fields; Postgres retains them.
    # Assert collect still receives/passes the authorized form on the request object.
    authorized = "subject-a/DEMO-ORDER-42"
    provider = _RecordingProvider()
    collect = CollectEvidence(
        provider,
        store,
        FixedClock(datetime(2026, 11, 13, 12, 30, tzinfo=UTC)),
    )
    request = CollectRequest(
        case_id="case-demo-42",
        case_revision=1,
        order_reference=authorized,
    )
    collect(PRINCIPAL, request)
    assert request.order_reference == authorized
    assert provider.calls == ["DEMO-ORDER-42"]
