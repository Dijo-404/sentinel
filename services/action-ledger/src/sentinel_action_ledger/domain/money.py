"""Integer minor-unit reservation invariant."""

from __future__ import annotations

from dataclasses import dataclass

from .errors import ConflictError, ValidationError


@dataclass(frozen=True, slots=True)
class PaymentBalance:
    captured_minor: int
    reserved_minor: int
    pending_minor: int
    refunded_minor: int

    def allocated(self) -> int:
        return self.reserved_minor + self.pending_minor + self.refunded_minor

    def remaining(self) -> int:
        return self.captured_minor - self.allocated()


def assert_can_reserve(balance: PaymentBalance, amount_minor: int) -> None:
    if amount_minor < 1:
        raise ValidationError("amount_minor must be positive")
    if amount_minor > balance.remaining():
        raise ConflictError(
            "Reservation would overrun eligible capture",
            code="INSUFFICIENT_ELIGIBLE",
        )


def apply_reserve(balance: PaymentBalance, amount_minor: int) -> PaymentBalance:
    assert_can_reserve(balance, amount_minor)
    return PaymentBalance(
        captured_minor=balance.captured_minor,
        reserved_minor=balance.reserved_minor + amount_minor,
        pending_minor=balance.pending_minor,
        refunded_minor=balance.refunded_minor,
    )


def reserved_to_pending(balance: PaymentBalance, amount_minor: int) -> PaymentBalance:
    if amount_minor > balance.reserved_minor:
        raise ConflictError("Insufficient reserved amount")
    return PaymentBalance(
        captured_minor=balance.captured_minor,
        reserved_minor=balance.reserved_minor - amount_minor,
        pending_minor=balance.pending_minor + amount_minor,
        refunded_minor=balance.refunded_minor,
    )


def reserved_or_pending_to_refunded(
    balance: PaymentBalance, amount_minor: int, *, from_pending: bool
) -> PaymentBalance:
    if from_pending:
        if amount_minor > balance.pending_minor:
            raise ConflictError("Insufficient pending amount")
        return PaymentBalance(
            captured_minor=balance.captured_minor,
            reserved_minor=balance.reserved_minor,
            pending_minor=balance.pending_minor - amount_minor,
            refunded_minor=balance.refunded_minor + amount_minor,
        )
    if amount_minor > balance.reserved_minor:
        raise ConflictError("Insufficient reserved amount")
    return PaymentBalance(
        captured_minor=balance.captured_minor,
        reserved_minor=balance.reserved_minor - amount_minor,
        pending_minor=balance.pending_minor,
        refunded_minor=balance.refunded_minor + amount_minor,
    )


def release_allocation(
    balance: PaymentBalance, amount_minor: int, *, from_pending: bool
) -> PaymentBalance:
    if from_pending:
        if amount_minor > balance.pending_minor:
            raise ConflictError("Insufficient pending amount to release")
        return PaymentBalance(
            captured_minor=balance.captured_minor,
            reserved_minor=balance.reserved_minor,
            pending_minor=balance.pending_minor - amount_minor,
            refunded_minor=balance.refunded_minor,
        )
    if amount_minor > balance.reserved_minor:
        raise ConflictError("Insufficient reserved amount to release")
    return PaymentBalance(
        captured_minor=balance.captured_minor,
        reserved_minor=balance.reserved_minor - amount_minor,
        pending_minor=balance.pending_minor,
        refunded_minor=balance.refunded_minor,
    )
