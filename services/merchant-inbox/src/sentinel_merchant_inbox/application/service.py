"""Merchant exception inbox use cases."""

from __future__ import annotations

from typing import Any

from sentinel_merchant_inbox.application.ports import CaseApiPort, EvidencePort, InboxStore
from sentinel_merchant_inbox.contracts import (
    KINDS,
    STATUSES,
    ExceptionItem,
    ExceptionKind,
    ExceptionStatus,
    MerchantBinding,
)
from sentinel_merchant_inbox.domain import rules
from sentinel_merchant_inbox.domain.errors import ForbiddenError, NotFoundError, ValidationError


class MerchantInboxService:
    def __init__(
        self,
        *,
        store: InboxStore,
        case_api: CaseApiPort,
        evidence: EvidencePort,
    ) -> None:
        self._store = store
        self._case_api = case_api
        self._evidence = evidence

    def list_exceptions(
        self,
        binding: MerchantBinding,
        *,
        merchant_ref: str,
        kind: str | None = None,
        status: str | None = None,
    ) -> list[ExceptionItem]:
        self._authorize(binding, merchant_ref)
        kind_f = self._parse_kind(kind)
        status_f = self._parse_status(status)
        return self._store.list_items(
            tenant_id=binding.principal.tenant_id,
            merchant_ref=merchant_ref,
            kind=kind_f,
            status=status_f,
        )

    def get_exception(
        self,
        binding: MerchantBinding,
        *,
        item_id: str,
        enrich: bool = True,
    ) -> dict[str, Any]:
        item = self._require_item(binding, item_id)
        payload = item.as_dict()
        payload["resolved"] = False
        if enrich and item.case_id:
            case = self._case_api.get_case(item.case_id)
            evidence = self._evidence.get_case_evidence(item.case_id)
            payload["case"] = case
            payload["evidence"] = evidence
        return payload

    def assign(
        self,
        binding: MerchantBinding,
        *,
        item_id: str,
        assignee: str,
    ) -> ExceptionItem:
        item = self._require_item(binding, item_id)
        updated = rules.apply_assign(item, assignee=assignee)
        return self._store.save_item(updated)

    def add_note(
        self,
        binding: MerchantBinding,
        *,
        item_id: str,
        note: str,
    ) -> ExceptionItem:
        item = self._require_item(binding, item_id)
        updated = rules.apply_note(item, note=note)
        return self._store.save_item(updated)

    def escalate(
        self,
        binding: MerchantBinding,
        *,
        item_id: str,
        reason_code: str,
        owner_queue: str = "SUPERVISOR",
    ) -> dict[str, Any]:
        item = self._require_item(binding, item_id)
        if item.case_id:
            if not binding.principal.allows_case(item.case_id):
                raise ForbiddenError("Case out of principal scope")
            case = self._case_api.get_case(item.case_id)
            revision = case.get("revision")
            if not isinstance(revision, int):
                raise ValidationError("Case peer returned malformed revision")
            # Peer escalate for case-linked items; failures stay visible.
            self._case_api.escalate(
                item.case_id,
                expected_revision=revision,
                reason_code=reason_code,
                owner_queue=owner_queue,
            )
            # Evidence read confirms peer availability; not treated as resolution proof.
            self._evidence.get_case_evidence(item.case_id)
        updated = rules.apply_escalate(item, reason_code=reason_code)
        rules.assert_escalation_not_resolution(updated)
        saved = self._store.save_item(updated)
        body = saved.as_dict()
        body["resolved"] = False
        body["financial_outcome"] = None
        return body

    def _require_item(self, binding: MerchantBinding, item_id: str) -> ExceptionItem:
        item = self._store.get_item(tenant_id=binding.principal.tenant_id, item_id=item_id)
        if item is None:
            raise NotFoundError()
        self._authorize(binding, item.merchant_ref)
        return item

    def _authorize(self, binding: MerchantBinding, merchant_ref: str) -> None:
        principal = binding.principal
        if not principal.is_merchant_staff():
            raise ForbiddenError("Merchant operator or supervisor role required")
        if not merchant_ref:
            raise ValidationError("merchant_ref is required")
        if not binding.allows_merchant(merchant_ref):
            raise ForbiddenError("Unauthorized merchant scope")

    @staticmethod
    def _parse_kind(kind: str | None) -> ExceptionKind | None:
        if kind is None or kind == "":
            return None
        if kind not in KINDS:
            raise ValidationError(f"Unknown kind filter: {kind}")
        return kind  # type: ignore[return-value]

    @staticmethod
    def _parse_status(status: str | None) -> ExceptionStatus | None:
        if status is None or status == "":
            return None
        if status not in STATUSES:
            raise ValidationError(f"Unknown status filter: {status}")
        return status  # type: ignore[return-value]
