"""Use cases: list and fetch stored evaluation.v1 RunReport rows."""

from __future__ import annotations

from typing import Any

from sentinel_evaluation.application.errors import NotFoundError, UnauthorizedError
from sentinel_evaluation.application.ports import ReportStore
from sentinel_evaluation.domain.models import Principal


class ReportQueryService:
    def __init__(self, store: ReportStore) -> None:
        self._store = store

    def list_reports(self, principal: Principal) -> tuple[dict[str, Any], ...]:
        _require_admin(principal)
        return self._store.list_reports()

    def get_report(self, principal: Principal, run_id: str) -> dict[str, Any]:
        _require_admin(principal)
        report = self._store.get_report(run_id)
        if report is None:
            raise NotFoundError(f"RunReport not found: {run_id}")
        return report


def _require_admin(principal: Principal) -> None:
    if not principal.is_platform_admin():
        raise UnauthorizedError("platform admin role required")
