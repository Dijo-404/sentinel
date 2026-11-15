"""Rolling UTC metrics window — same algorithm as apps/web rollingMetricsWindow."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta


def rolling_metrics_window(
    now: datetime | None = None,
    day_count: int = 14,
) -> tuple[str, str]:
    """Return (window_start, window_end) as RFC 3339 UTC with Z suffix."""
    instant = now or datetime.now(UTC)
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=UTC)
    else:
        instant = instant.astimezone(UTC)
    end = datetime(instant.year, instant.month, instant.day, 23, 59, 59, tzinfo=UTC)
    days = max(day_count, 1)
    start = end - timedelta(days=days - 1)
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    return (
        start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        end.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
