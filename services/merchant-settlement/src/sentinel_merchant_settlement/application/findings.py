"""List, assign and close owned discrepancy findings."""

from __future__ import annotations

from sentinel_merchant_settlement.application.errors import (
    ForbiddenError,
    NotFoundError,
    ValidationError,
)
from sentinel_merchant_settlement.application.ports import FindingStore
from sentinel_merchant_settlement.domain.types import Principal, SettlementFinding


class ManageFindings:
    def __init__(self, store: FindingStore) -> None:
        self._store = store

    def list(
        self,
        principal: Principal,
        *,
        batch_id: str | None = None,
        status: str | None = None,
    ) -> list[SettlementFinding]:
        self._require_ops(principal)
        if status is not None and status not in {"OPEN", "ASSIGNED", "ESCALATED", "CLOSED"}:
            raise ValidationError("invalid status filter")
        findings = self._store.list_findings(batch_id=batch_id, status=status)
        return [f for f in findings if self._visible(principal, f)]

    def assign(self, principal: Principal, finding_id: str, assignee: str) -> SettlementFinding:
        self._require_ops(principal)
        if not assignee:
            raise ValidationError("assignee is required")
        finding = self._require_finding(principal, finding_id)
        if finding.status == "CLOSED":
            raise ValidationError("closed findings cannot be assigned")
        finding.status = "ASSIGNED"
        finding.assignee = assignee
        return self._store.update_finding(finding)

    def close(self, principal: Principal, finding_id: str) -> SettlementFinding:
        self._require_ops(principal)
        finding = self._require_finding(principal, finding_id)
        finding.status = "CLOSED"
        return self._store.update_finding(finding)

    def get_batch(self, principal: Principal, batch_id: str):
        self._require_ops(principal)
        batch = self._store.get_batch(batch_id)
        if batch is None:
            raise NotFoundError("Batch not found")
        if principal.tenant_id != batch.tenant_id:
            raise ForbiddenError("Tenant scope denied")
        if not principal.allows_merchant(batch.merchant_ref):
            raise ForbiddenError("Merchant scope denied")
        return batch

    def _require_ops(self, principal: Principal) -> None:
        if not {"operator", "supervisor"} & set(principal.roles):
            raise ForbiddenError("operator or supervisor role required")

    def _require_finding(self, principal: Principal, finding_id: str) -> SettlementFinding:
        finding = self._store.get_finding(finding_id)
        if finding is None or not self._visible(principal, finding):
            raise NotFoundError("Finding not found")
        return finding

    def _visible(self, principal: Principal, finding: SettlementFinding) -> bool:
        batch = self._store.get_batch(finding.batch_id)
        if batch is None:
            return False
        if principal.tenant_id != batch.tenant_id:
            return False
        return principal.allows_merchant(batch.merchant_ref)
