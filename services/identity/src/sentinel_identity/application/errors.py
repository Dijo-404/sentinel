"""Application-boundary errors mapped to HTTP by the adapter layer."""

from __future__ import annotations


class IdentityError(Exception):
    code: str
    http_status: int

    def __init__(self, message: str, *, request_id: str = "request-local"):
        super().__init__(message)
        self.message = message
        self.request_id = request_id


class UnauthorizedError(IdentityError):
    code = "UNAUTHORIZED"
    http_status = 401


class ForbiddenError(IdentityError):
    code = "FORBIDDEN"
    http_status = 403


class NotFoundError(IdentityError):
    code = "NOT_FOUND"
    http_status = 404


class ValidationError(IdentityError):
    code = "INVALID_INPUT"
    http_status = 422


class InvalidChallengeError(IdentityError):
    """Bad / expired / missing auth challenge (generic; no enumeration)."""

    code = "INVALID_CHALLENGE"
    http_status = 400


class ConflictError(IdentityError):
    code = "CONFLICT"
    http_status = 409


class ConfigurationError(IdentityError):
    code = "CONFIGURATION"
    http_status = 500
