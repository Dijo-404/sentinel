"""Local double: any ledger approval attempt is forbidden for risk principals."""

from sentinel_risk.application.errors import LedgerApprovalForbiddenError


def approve(*_args, **_kwargs):
    raise LedgerApprovalForbiddenError(
        "Risk officers cannot approve ledger refunds or financial actions"
    )
