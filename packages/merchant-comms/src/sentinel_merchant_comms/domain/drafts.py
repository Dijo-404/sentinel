"""CommsDraft state transitions. Models propose text only; no financial authority."""

from __future__ import annotations

from sentinel_merchant_comms.domain.types import CommsDraft, DeliveryEvent, DraftStatus


class DraftTransitionError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def approve(draft: CommsDraft) -> CommsDraft:
    _require_status(draft, {"DRAFT"}, "APPROVE")
    return draft.model_copy(update={"status": "APPROVED"})


def reject(draft: CommsDraft) -> CommsDraft:
    _require_status(draft, {"DRAFT"}, "REJECT")
    return draft.model_copy(update={"status": "REJECTED"})


def simulate_send(draft: CommsDraft, *, at: str, channel: str) -> CommsDraft:
    if draft.status == "REJECTED":
        raise DraftTransitionError(
            "DRAFT_REJECTED",
            "Rejected drafts are not delivered",
        )
    if draft.status == "DRAFT":
        raise DraftTransitionError(
            "APPROVAL_REQUIRED",
            "Operator approval required before simulated send",
        )
    if draft.status == "SIMULATED_SENT":
        raise DraftTransitionError(
            "ALREADY_SENT",
            "Draft already simulated as sent",
        )
    if draft.status != "APPROVED":
        raise DraftTransitionError(
            "INVALID_STATUS",
            f"Cannot simulate send from status {draft.status}",
        )
    event = DeliveryEvent(at=at, channel=channel, status="SIMULATED_SENT")
    history = list(draft.delivery_history) + [event]
    return draft.model_copy(update={"status": "SIMULATED_SENT", "delivery_history": history})


def _require_status(draft: CommsDraft, allowed: set[DraftStatus], action: str) -> None:
    if draft.status not in allowed:
        raise DraftTransitionError(
            "INVALID_STATUS",
            f"Cannot {action} draft in status {draft.status}",
        )
