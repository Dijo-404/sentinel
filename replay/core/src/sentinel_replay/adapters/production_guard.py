from __future__ import annotations

PRODUCTION_WRITE_PREFIXES = (
    "https://api.paytm.com/",
    "https://securegw.paytm.in/",
    "prod://payments/",
    "production://write/",
)

PRODUCTION_NOTIFICATION_PREFIXES = (
    "https://notify.production/",
    "prod://notify/",
    "production://notify/",
)


class ProductionRouteBlocked(RuntimeError):
    """Raised when replay attempts a production write or notification route."""


def assert_sandbox_route(route: str) -> None:
    lowered = route.lower()
    for prefix in PRODUCTION_WRITE_PREFIXES:
        if lowered.startswith(prefix):
            raise ProductionRouteBlocked(f"replay blocks production write route: {route}")
    for prefix in PRODUCTION_NOTIFICATION_PREFIXES:
        if lowered.startswith(prefix):
            raise ProductionRouteBlocked(f"replay blocks production notification route: {route}")


class ProductionGuard:
    """Records that production write/notification routes stay blocked for a run."""

    def __init__(self) -> None:
        self.writes_blocked = True
        self.notifications_blocked = True
        self.blocked_attempts: list[str] = []

    def check_write(self, route: str) -> None:
        try:
            assert_sandbox_route(route)
        except ProductionRouteBlocked:
            self.blocked_attempts.append(route)
            raise

    def check_notification(self, route: str) -> None:
        try:
            assert_sandbox_route(route)
        except ProductionRouteBlocked:
            self.blocked_attempts.append(route)
            raise
