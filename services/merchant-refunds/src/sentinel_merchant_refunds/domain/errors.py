"""Typed application/domain errors with HTTP mapping."""

from __future__ import annotations


class MerchantRefundsError(Exception):
    code = "MERCHANT_REFUNDS_ERROR"
    http_status = 500

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ValidationError(MerchantRefundsError):
    code = "INVALID_INPUT"
    http_status = 422


class UnauthorizedError(MerchantRefundsError):
    code = "UNAUTHORIZED"
    http_status = 403


class NotFoundError(MerchantRefundsError):
    code = "NOT_FOUND"
    http_status = 404


class ConflictError(MerchantRefundsError):
    code = "CONFLICT"
    http_status = 409


class PeerError(MerchantRefundsError):
    code = "PEER_ERROR"
    http_status = 502

    def __init__(self, code: str, message: str, *, status_code: int = 502) -> None:
        super().__init__(message)
        self.code = code
        self.http_status = status_code


class PeerUnavailableError(PeerError):
    def __init__(self, peer: str) -> None:
        super().__init__("PEER_UNAVAILABLE", f"Required peer unavailable: {peer}", status_code=503)
