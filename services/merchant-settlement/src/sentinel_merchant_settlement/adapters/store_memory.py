"""In-process finding/batch store for fixture and local checks."""

from __future__ import annotations

from sentinel_merchant_settlement.domain.types import SettlementBatch, SettlementFinding


class MemoryFindingStore:
    def __init__(self) -> None:
        self._batches: dict[str, SettlementBatch] = {}
        self._findings: dict[str, SettlementFinding] = {}

    def save_import(self, batch: SettlementBatch, findings: list[SettlementFinding]) -> None:
        self._batches[batch.batch_id] = batch
        for finding in findings:
            self._findings[finding.finding_id] = finding

    def get_batch(self, batch_id: str) -> SettlementBatch | None:
        return self._batches.get(batch_id)

    def list_findings(
        self, *, batch_id: str | None = None, status: str | None = None
    ) -> list[SettlementFinding]:
        items = list(self._findings.values())
        if batch_id is not None:
            items = [f for f in items if f.batch_id == batch_id]
        if status is not None:
            items = [f for f in items if f.status == status]
        return sorted(items, key=lambda f: f.finding_id)

    def get_finding(self, finding_id: str) -> SettlementFinding | None:
        return self._findings.get(finding_id)

    def update_finding(self, finding: SettlementFinding) -> SettlementFinding:
        self._findings[finding.finding_id] = finding
        return finding
