"""Merchant list access preserves tenant, merchant, case and write boundaries."""

from dataclasses import replace

import pytest

from sentinel_merchant_disputes.application.errors import UnauthorizedError
from sentinel_merchant_disputes.domain.types import CreateDisputeRequest
from tests.conftest import OPERATOR


def test_merchant_can_list_only_scoped_disputes_and_cannot_mutate(service):
    dispute = service.create(
        OPERATOR,
        CreateDisputeRequest(
            case_id="case-demo-42",
            merchant_ref="merchant-demo",
            reason_code="DUPLICATE",
            order_reference="DEMO-ORDER-42",
            deadline_at="2026-11-20T12:30:00Z",
        ),
    )
    merchant = replace(OPERATOR, roles=("merchant",))
    assert service.list(merchant, "merchant-demo") == (dispute,)
    assert service.list(replace(merchant, tenant_id="other"), "merchant-demo") == ()
    assert service.list(replace(merchant, case_ids=()), "merchant-demo") == ()
    with pytest.raises(UnauthorizedError):
        service.list(merchant, "other-merchant")
    with pytest.raises(UnauthorizedError):
        service.collect_packet(merchant, dispute.dispute_id)
    with pytest.raises(UnauthorizedError):
        service.list(replace(merchant, roles=("customer",)), "merchant-demo")
