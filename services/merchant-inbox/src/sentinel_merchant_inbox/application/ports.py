"""Narrow ports. No ledger authority."""

from __future__ import annotations

from typing import Any, Protocol

from sentinel_merchant_inbox.contracts import ExceptionItem, ExceptionKind, ExceptionStatus


class InboxStore(Protocol):
    def list_items(
        self,
        *,
        tenant_id: str,
        merchant_ref: str,
        kind: ExceptionKind | None = None,
        status: ExceptionStatus | None = None,
    ) -> list[ExceptionItem]: ...

    def get_item(self, *, tenant_id: str, item_id: str) -> ExceptionItem | None: ...

    def save_item(self, item: ExceptionItem) -> ExceptionItem: ...


class CaseApiPort(Protocol):
    def get_case(self, case_id: str) -> dict[str, Any]: ...

    def escalate(
        self,
        case_id: str,
        *,
        expected_revision: int,
        reason_code: str,
        owner_queue: str,
    ) -> dict[str, Any]: ...


class EvidencePort(Protocol):
    def get_case_evidence(self, case_id: str) -> dict[str, Any]: ...
