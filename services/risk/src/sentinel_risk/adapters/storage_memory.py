"""In-memory risk store for fixture mode and unit tests."""

from __future__ import annotations

import threading

from ..application.errors import ConflictError
from ..domain.types import Finding, Investigation, RiskRestriction


class MemoryRiskStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._investigations: dict[str, Investigation] = {}
        self._findings: dict[str, Finding] = {}
        self._restrictions: dict[str, RiskRestriction] = {}
        self._by_idempotency: dict[str, str] = {}
        self._idempotency_payload: dict[str, str] = {}

    def create_investigation(
        self,
        investigation: Investigation,
        restriction: RiskRestriction,
        *,
        idempotency_key: str | None,
    ) -> Investigation:
        if idempotency_key:
            fingerprint = _fingerprint(investigation)
            existing_id = self._by_idempotency.get(idempotency_key)
            if existing_id is not None:
                if self._idempotency_payload[idempotency_key] != fingerprint:
                    raise ConflictError("Idempotency-Key already used with a different payload")
                return self._investigations[existing_id]
            self._by_idempotency[idempotency_key] = investigation.investigation_id
            self._idempotency_payload[idempotency_key] = fingerprint
        self._investigations[investigation.investigation_id] = investigation
        self._restrictions[restriction.restriction_id] = restriction
        return investigation

    def get_investigation(self, investigation_id: str) -> Investigation | None:
        return self._investigations.get(investigation_id)

    def list_investigations(
        self,
        *,
        tenant_id: str,
        case_id: str | None = None,
    ) -> tuple[Investigation, ...]:
        items = [
            inv
            for inv in self._investigations.values()
            if inv.tenant_id == tenant_id and (case_id is None or inv.case_id == case_id)
        ]
        return tuple(sorted(items, key=lambda i: i.created_at, reverse=True))

    def save_investigation(self, investigation: Investigation) -> Investigation:
        if investigation.investigation_id not in self._investigations:
            raise ConflictError("Unknown investigation")
        self._investigations[investigation.investigation_id] = investigation
        return investigation

    def save_finding(self, finding: Finding) -> Finding:
        self._findings[finding.finding_id] = finding
        return finding

    def list_findings(self, investigation_id: str) -> tuple[Finding, ...]:
        return tuple(f for f in self._findings.values() if f.investigation_id == investigation_id)

    def get_restriction(self, restriction_id: str) -> RiskRestriction | None:
        return self._restrictions.get(restriction_id)

    def save_restriction(self, restriction: RiskRestriction) -> RiskRestriction:
        with self._lock:
            if restriction.restriction_id not in self._restrictions:
                raise ConflictError("Unknown restriction")
            # Hard invariant: never persist a money approval from risk.
            if restriction.financial_approval_granted:
                raise ConflictError("Risk store refuses financial_approval_granted=true")
            self._restrictions[restriction.restriction_id] = restriction
            return restriction

    def compare_and_swap_restriction(
        self,
        restriction: RiskRestriction,
        *,
        expected_revision: int,
    ) -> RiskRestriction:
        with self._lock:
            current = self._restrictions.get(restriction.restriction_id)
            if current is None:
                raise ConflictError("Unknown restriction")
            if current.revision != expected_revision:
                raise ConflictError("Restriction revision mismatch")
            if restriction.financial_approval_granted:
                raise ConflictError("Risk store refuses financial_approval_granted=true")
            self._restrictions[restriction.restriction_id] = restriction
            return restriction

    def list_restrictions(
        self,
        *,
        tenant_id: str,
        case_id: str | None = None,
        investigation_id: str | None = None,
    ) -> tuple[RiskRestriction, ...]:
        items = []
        for restriction in self._restrictions.values():
            if restriction.tenant_id != tenant_id:
                continue
            if case_id is not None and restriction.case_id != case_id:
                continue
            if investigation_id is not None and restriction.investigation_id != investigation_id:
                continue
            items.append(restriction)
        return tuple(items)


def _fingerprint(investigation: Investigation) -> str:
    return "|".join(
        [
            investigation.tenant_id,
            investigation.case_id,
            investigation.reason_code,
            investigation.queue_ref,
            str(investigation.case_revision),
        ]
    )
