"""Domain and application failure kinds mapped to HTTP at the adapter edge."""


class InboxError(Exception):
    def __init__(self, code: str, message: str, *, http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


class ForbiddenError(InboxError):
    def __init__(self, message: str = "Unauthorized merchant scope") -> None:
        super().__init__("FORBIDDEN", message, http_status=403)


class NotFoundError(InboxError):
    def __init__(self, message: str = "Exception item not found") -> None:
        super().__init__("NOT_FOUND", message, http_status=404)


class ValidationError(InboxError):
    def __init__(self, message: str, *, code: str = "INVALID_INPUT") -> None:
        super().__init__(code, message, http_status=422)


class ConflictError(InboxError):
    def __init__(self, message: str, *, code: str = "CONFLICT") -> None:
        super().__init__(code, message, http_status=409)


class UnauthorizedError(InboxError):
    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__("UNAUTHORIZED", message, http_status=401)


class PeerUnavailableError(InboxError):
    def __init__(self, message: str = "Required peer unavailable") -> None:
        super().__init__("PEER_UNAVAILABLE", message, http_status=503)


class PeerError(InboxError):
    def __init__(self, code: str, message: str, *, status_code: int = 502) -> None:
        super().__init__(code, message, http_status=status_code)
