"""Application/peer errors mapped to HTTP by the adapter."""

from __future__ import annotations


class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class NotFoundError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__("NOT_FOUND", message, 404)


class ForbiddenError(AppError):
    def __init__(self, message: str = "out of scope") -> None:
        super().__init__("FORBIDDEN", message, 403)


class ConflictError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__("CONFLICT", message, 409)


class PeerUnavailableError(AppError):
    def __init__(self, peer: str = "case-api") -> None:
        super().__init__("PEER_UNAVAILABLE", f"{peer} unavailable", 503)


class PeerUnauthorizedError(AppError):
    def __init__(self, message: str = "peer unauthorized or out of scope") -> None:
        super().__init__("UNAUTHORIZED", message, 403)


class PeerMalformedError(AppError):
    def __init__(self, message: str = "peer returned malformed payload") -> None:
        super().__init__("MALFORMED", message, 502)


class ConfigurationError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__("INVALID_CONFIG", message, 500)
