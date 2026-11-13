"""Stub modules expose the four required peer behaviors."""

from __future__ import annotations

import pytest

from sentinel_merchant_disputes.application.errors import (
    PeerMalformedError,
    PeerUnauthorizedError,
    PeerUnavailableError,
)
from sentinel_merchant_disputes.domain.types import Principal
from tests.stubs import (
    case_api_malformed,
    case_api_unauthorized,
    case_api_unavailable,
    case_api_valid,
    evidence_malformed,
    evidence_unauthorized,
    evidence_unavailable,
    evidence_valid,
)

PRINCIPAL = Principal(
    "op-1",
    "tenant-demo",
    ("operator",),
    ("subj-demo-1",),
    ("case-demo-42",),
    ("merchant-demo",),
)


def test_case_api_stub_behaviors():
    case = case_api_valid.PEER.get_case("case-demo-42", principal=PRINCIPAL)
    assert case.case_id == "case-demo-42"

    with pytest.raises(PeerUnavailableError):
        case_api_unavailable.PEER.get_case("case-demo-42", principal=PRINCIPAL)
    with pytest.raises(PeerMalformedError):
        case_api_malformed.PEER.get_case("case-demo-42", principal=PRINCIPAL)
    with pytest.raises(PeerUnauthorizedError):
        case_api_unauthorized.PEER.get_case("case-demo-42", principal=PRINCIPAL)


def test_evidence_stub_behaviors():
    bundle = evidence_valid.PEER.collect(
        case_id="case-demo-42",
        case_revision=1,
        order_reference="DEMO-ORDER-42",
        principal=PRINCIPAL,
    )
    kinds = {item.kind for item in bundle.evidence}
    assert kinds >= {"PAYMENT", "ORDER", "DELIVERY"}

    with pytest.raises(PeerUnavailableError):
        evidence_unavailable.PEER.collect(
            case_id="case-demo-42",
            case_revision=1,
            order_reference="DEMO-ORDER-42",
            principal=PRINCIPAL,
        )
    with pytest.raises(PeerMalformedError):
        evidence_malformed.PEER.collect(
            case_id="case-demo-42",
            case_revision=1,
            order_reference="DEMO-ORDER-42",
            principal=PRINCIPAL,
        )
    with pytest.raises(PeerUnauthorizedError):
        evidence_unauthorized.PEER.collect(
            case_id="case-demo-42",
            case_revision=1,
            order_reference="DEMO-ORDER-42",
            principal=PRINCIPAL,
        )
