"""Peer stub cases: valid / unavailable / malformed / unauthorized."""

from __future__ import annotations

import pytest
from tests.stubs.evidence import malformed as evidence_malformed
from tests.stubs.evidence import unauthorized_or_out_of_scope as evidence_unauthorized
from tests.stubs.evidence import unavailable as evidence_unavailable
from tests.stubs.evidence import valid as evidence_valid
from tests.stubs.payment_provider import malformed as provider_malformed
from tests.stubs.payment_provider import unauthorized_or_out_of_scope as provider_unauthorized
from tests.stubs.payment_provider import unavailable as provider_unavailable
from tests.stubs.payment_provider import valid as provider_valid

from sentinel_merchant_settlement.application.errors import (
    PeerMalformedError,
    PeerUnauthorizedError,
    PeerUnavailableError,
)
from sentinel_merchant_settlement.domain.types import Principal

PRINCIPAL = Principal(
    "op-demo",
    "demo-tenant-a",
    ("operator",),
    ("merchant:demo-merchant-1",),
    ("*",),
)


def test_evidence_stub_cases():
    world = evidence_valid.EVIDENCE.load_world(
        principal=PRINCIPAL,
        tenant_id="demo-tenant-a",
        merchant_ref="demo-merchant-1",
        order_refs=("ORDER-OK",),
        transaction_refs=("TXN-OK",),
    )
    assert world.evidence

    with pytest.raises(PeerUnavailableError):
        evidence_unavailable.EVIDENCE.load_world(
            principal=PRINCIPAL,
            tenant_id="demo-tenant-a",
            merchant_ref="demo-merchant-1",
            order_refs=(),
            transaction_refs=(),
        )
    with pytest.raises(PeerMalformedError):
        evidence_malformed.EVIDENCE.load_world(
            principal=PRINCIPAL,
            tenant_id="demo-tenant-a",
            merchant_ref="demo-merchant-1",
            order_refs=(),
            transaction_refs=(),
        )
    with pytest.raises(PeerUnauthorizedError):
        evidence_unauthorized.EVIDENCE.load_world(
            principal=PRINCIPAL,
            tenant_id="demo-tenant-a",
            merchant_ref="demo-merchant-1",
            order_refs=(),
            transaction_refs=(),
        )


def test_provider_stub_cases():
    world = provider_valid.PROVIDER.load_world(
        principal=PRINCIPAL,
        tenant_id="demo-tenant-a",
        merchant_ref="demo-merchant-1",
        period_start="2026-11-01T00:00:00Z",
        period_end="2026-11-30T23:59:59Z",
        order_refs=("ORDER-OK",),
        transaction_refs=("TXN-OK",),
    )
    assert world.payments

    with pytest.raises(PeerUnavailableError):
        provider_unavailable.PROVIDER.load_world(
            principal=PRINCIPAL,
            tenant_id="demo-tenant-a",
            merchant_ref="demo-merchant-1",
            period_start="2026-11-01T00:00:00Z",
            period_end="2026-11-30T23:59:59Z",
            order_refs=(),
            transaction_refs=(),
        )
    with pytest.raises(PeerMalformedError):
        provider_malformed.PROVIDER.load_world(
            principal=PRINCIPAL,
            tenant_id="demo-tenant-a",
            merchant_ref="demo-merchant-1",
            period_start="2026-11-01T00:00:00Z",
            period_end="2026-11-30T23:59:59Z",
            order_refs=(),
            transaction_refs=(),
        )
    with pytest.raises(PeerUnauthorizedError):
        provider_unauthorized.PROVIDER.load_world(
            principal=PRINCIPAL,
            tenant_id="demo-tenant-a",
            merchant_ref="demo-merchant-1",
            period_start="2026-11-01T00:00:00Z",
            period_end="2026-11-30T23:59:59Z",
            order_refs=(),
            transaction_refs=(),
        )
