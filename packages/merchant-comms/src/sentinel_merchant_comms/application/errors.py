"""Application errors. Never embed credentials or raw peer payloads."""

from __future__ import annotations


class MerchantCommsError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class ConfigurationError(MerchantCommsError):
    def __init__(self, message: str) -> None:
        super().__init__("CONFIGURATION_ERROR", message, 500)


class UnauthorizedError(MerchantCommsError):
    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__("UNAUTHORIZED", message, 401)


class ForbiddenError(MerchantCommsError):
    def __init__(self, message: str = "Forbidden") -> None:
        super().__init__("FORBIDDEN", message, 403)


class NotFoundError(MerchantCommsError):
    def __init__(self, message: str = "Not found") -> None:
        super().__init__("NOT_FOUND", message, 404)


class ConflictError(MerchantCommsError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code, message, 409)


class PeerUnavailableError(MerchantCommsError):
    def __init__(self, peer: str, message: str = "Required peer unavailable") -> None:
        super().__init__("PEER_UNAVAILABLE", f"{peer}: {message}", 503)


class PeerMalformedError(MerchantCommsError):
    def __init__(self, peer: str, message: str = "Peer returned malformed payload") -> None:
        super().__init__("MALFORMED_RESPONSE", f"{peer}: {message}", 502)


class PeerUnauthorizedError(MerchantCommsError):
    def __init__(self, peer: str, message: str = "Resource not found") -> None:
        # Same surface for unauthorized/out-of-scope to avoid existence leaks.
        super().__init__("NOT_FOUND", f"{peer}: {message}", 404)
