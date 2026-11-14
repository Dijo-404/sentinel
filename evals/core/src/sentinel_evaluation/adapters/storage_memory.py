"""In-memory RunReport store for fixture mode and unit tests."""

from __future__ import annotations

from typing import Any


class MemoryReportStore:
    def __init__(self) -> None:
        self._reports: dict[str, dict[str, Any]] = {}

    def put_report(self, report: dict[str, Any]) -> dict[str, Any]:
        run_id = str(report["run_id"])
        self._reports[run_id] = dict(report)
        return self._reports[run_id]

    def get_report(self, run_id: str) -> dict[str, Any] | None:
        found = self._reports.get(run_id)
        return dict(found) if found is not None else None

    def list_reports(self) -> tuple[dict[str, Any], ...]:
        items = sorted(self._reports.values(), key=lambda r: str(r["run_id"]))
        return tuple(dict(item) for item in items)
