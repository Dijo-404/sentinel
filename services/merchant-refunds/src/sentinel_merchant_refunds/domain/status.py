"""Map ledger action status onto merchant request status. Fail closed on unknowns."""

from __future__ import annotations

from sentinel_merchant_refunds.domain.errors import ValidationError
from sentinel_merchant_refunds.domain.types import (
    CREDIT_VERIFIED_LEDGER_STATUSES,
    FAILED_LEDGER_STATUSES,
    RequestStatus,
)


def map_ledger_status(ledger_status: str) -> RequestStatus:
    """Translate authoritative ledger status. PENDING is never VERIFIED."""
    if ledger_status in CREDIT_VERIFIED_LEDGER_STATUSES:
        return "VERIFIED"
    if ledger_status in FAILED_LEDGER_STATUSES:
        return "FAILED"
    if ledger_status == "RESERVED":
        return "RESERVED"
    if ledger_status == "PROPOSED":
        return "AWAITING_APPROVAL"
    if ledger_status in {
        "DISPATCHING",
        "OUTCOME_UNKNOWN",
        "PENDING",
        "PROVIDER_CONFIRMED",
        "ESCALATED",
    }:
        # Still reserved / in flight. Not customer credit.
        return "RESERVED"
    raise ValidationError(f"Unknown ledger status: {ledger_status}")


def is_customer_credit(ledger_status: str | None, request_status: RequestStatus) -> bool:
    return request_status == "VERIFIED" and ledger_status in CREDIT_VERIFIED_LEDGER_STATUSES
