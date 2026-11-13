"""Application errors. Never embed credentials or raw provider secrets."""

from __future__ import annotations


class IndicContextError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class ConfigurationError(IndicContextError):
    def __init__(self, message: str) -> None:
        super().__init__("CONFIGURATION_ERROR", message, 500)


class UnauthorizedError(IndicContextError):
    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__("UNAUTHORIZED", message, 401)


class ForbiddenError(IndicContextError):
    def __init__(self, message: str = "Forbidden") -> None:
        super().__init__("FORBIDDEN", message, 403)


class ProviderUnavailableError(IndicContextError):
    def __init__(self, message: str = "Provider unavailable") -> None:
        super().__init__("PROVIDER_UNAVAILABLE", message, 502)


class ProviderError(IndicContextError):
    def __init__(self, code: str, message: str, status_code: int = 502) -> None:
        super().__init__(code, message, status_code)
