"""Application-boundary errors mapped to HTTP by the adapter layer."""

from __future__ import annotations


class TeamsError(Exception):
    code: str
    http_status: int

    def __init__(self, message: str, *, request_id: str = "request-local"):
        super().__init__(message)
        self.message = message
        self.request_id = request_id


class UnauthorizedError(TeamsError):
    code = "FORBIDDEN"
    http_status = 403


class NotFoundError(TeamsError):
    code = "NOT_FOUND"
    http_status = 404


class ValidationError(TeamsError):
    code = "INVALID_INPUT"
    http_status = 422


class ConflictError(TeamsError):
    code = "CONFLICT"
    http_status = 409


class PeerUnavailableError(TeamsError):
    code = "PEER_UNAVAILABLE"
    http_status = 503


class PeerUnauthorizedError(TeamsError):
    code = "PEER_UNAUTHORIZED"
    http_status = 403


class PeerMalformedError(TeamsError):
    code = "PEER_MALFORMED"
    http_status = 502


class ConfigurationError(TeamsError):
    code = "CONFIGURATION"
    http_status = 500


class FinancialAuthorityDenied(TeamsError):
    """Raised when a caller attempts to treat advisory limits as money authority."""

    code = "FINANCIAL_AUTHORITY_DENIED"
    http_status = 403
