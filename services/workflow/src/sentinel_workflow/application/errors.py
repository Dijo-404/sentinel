"""Application-level errors mapped to HTTP envelopes by adapters."""

from __future__ import annotations


class WorkflowError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class UnauthorizedError(WorkflowError):
    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__("UNAUTHORIZED", message, 403)


class IdempotencyConflictError(WorkflowError):
    def __init__(self, message: str = "Key already used with a different payload") -> None:
        super().__init__("IDEMPOTENCY_CONFLICT", message, 409)


class ValidationError(WorkflowError):
    def __init__(self, message: str) -> None:
        super().__init__("INVALID_REQUEST", message, 422)


class PeerUnavailableError(WorkflowError):
    def __init__(self, peer: str) -> None:
        super().__init__("PEER_UNAVAILABLE", f"Required peer unavailable: {peer}", 503)


class PeerError(WorkflowError):
    def __init__(self, code: str, message: str, status_code: int = 502) -> None:
        super().__init__(code, message, status_code)
