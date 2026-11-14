"""List tenant-scoped activity feed."""

from __future__ import annotations

from ..domain.types import ALLOWED_ROLES, FEED_LIMIT, ActivityItem, Principal
from .errors import UnauthorizedError
from .ports import ActivityStore


class ActivityService:
    def __init__(self, store: ActivityStore):
        self._store = store

    def list_activity(self, principal: Principal) -> list[ActivityItem]:
        if not ALLOWED_ROLES.intersection(principal.roles):
            raise UnauthorizedError("operator or supervisor role required")
        return self._store.list_activity(principal.tenant_id, limit=FEED_LIMIT)
