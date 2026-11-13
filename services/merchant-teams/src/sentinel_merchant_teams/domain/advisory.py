"""Advisory approval limits — metadata only, never financial authority."""

from __future__ import annotations

from .types import AdvisoryLimitResult, MerchantStaff


def check_advisory_limit(
    staff: MerchantStaff,
    *,
    amount_minor: int,
    currency: str,
) -> AdvisoryLimitResult:
    """Compare amount to staff advisory metadata. Never mints approval/reservation."""
    if amount_minor <= 0:
        raise ValueError("amount_minor must be a positive integer")
    if not currency:
        raise ValueError("currency is required")

    within = False
    if staff.active and staff.approval_limit_minor is not None:
        staff_currency = staff.currency or currency
        if staff_currency == currency and amount_minor <= staff.approval_limit_minor:
            within = True

    return AdvisoryLimitResult(
        staff_id=staff.staff_id,
        amount_minor=amount_minor,
        currency=currency,
        within_advisory_limit=within,
        advisory=True,
        authorizes_ledger_or_provider=False,
        approval_id=None,
        reservation_id=None,
    )


def refuse_financial_authorization(*, reason: str = "advisory_limit") -> None:
    """Hard stop: merchant-teams must never authorize ledger or provider writes."""
    del reason
    raise PermissionError(
        "Merchant approval limits are advisory only and cannot authorize "
        "ledger reservations, approvals, or provider writes"
    )
