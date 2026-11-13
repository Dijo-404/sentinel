from __future__ import annotations

import json
from typing import Any

from .models import RefundRequest


class DomainError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ValidationError(DomainError):
    def __init__(self, message: str, code: str = "INVALID_INPUT") -> None:
        super().__init__(code, message)


class IdempotencyConflict(DomainError):
    def __init__(self, message: str = "Key already used with a different payload") -> None:
        super().__init__("IDEMPOTENCY_CONFLICT", message)


class NotFound(DomainError):
    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__("NOT_FOUND", message)


class Unauthorized(DomainError):
    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__("UNAUTHORIZED", message)


class Unavailable(DomainError):
    def __init__(self, message: str = "Provider outage") -> None:
        super().__init__("PROVIDER_OUTAGE", message)


class TimeoutAfterAccept(DomainError):
    """Raised after the refund side effect is durable; caller must recover by reference."""

    def __init__(self, provider_ref: str) -> None:
        super().__init__(
            "TIMEOUT_AFTER_ACCEPT",
            f"Accepted refund {provider_ref} then timed out; recover by provider_ref",
        )
        self.provider_ref = provider_ref


def assert_inr_minor(amount_minor: Any, currency: Any) -> None:
    if not isinstance(amount_minor, int) or isinstance(amount_minor, bool):
        raise ValidationError("amount_minor must be an integer minor-unit value")
    if amount_minor < 1:
        raise ValidationError("amount_minor must be a positive integer")
    if currency != "INR":
        raise ValidationError("currency must be INR")


def assert_refund_request(body: dict[str, Any], idempotency_key: str | None) -> RefundRequest:
    required = (
        "action_id",
        "provider_ref",
        "transaction_ref",
        "amount_minor",
        "currency",
        "destination",
    )
    extra = set(body) - set(required)
    if extra:
        raise ValidationError(f"undeclared fields: {sorted(extra)}")
    missing = [key for key in required if key not in body]
    if missing:
        raise ValidationError(f"missing fields: {missing}")
    if not idempotency_key:
        raise ValidationError("Idempotency-Key header is required")
    provider_ref = body["provider_ref"]
    if not isinstance(provider_ref, str) or not provider_ref:
        raise ValidationError("provider_ref must be a nonempty string")
    if idempotency_key != provider_ref:
        raise ValidationError("Idempotency-Key must equal provider_ref")
    for key in ("action_id", "transaction_ref"):
        value = body[key]
        if not isinstance(value, str) or not value:
            raise ValidationError(f"{key} must be a nonempty string")
    assert_inr_minor(body["amount_minor"], body["currency"])
    if body["destination"] != "ORIGINAL_PAYMENT_ROUTE":
        raise ValidationError("destination must be ORIGINAL_PAYMENT_ROUTE")
    return RefundRequest(
        action_id=body["action_id"],
        provider_ref=provider_ref,
        transaction_ref=body["transaction_ref"],
        amount_minor=body["amount_minor"],
        currency="INR",
        destination="ORIGINAL_PAYMENT_ROUTE",
    )


def refund_fingerprint(request: RefundRequest) -> str:
    payload = request.to_dict()
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
