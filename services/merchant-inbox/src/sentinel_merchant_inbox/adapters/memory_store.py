"""In-memory exception store for fixture-mode standalone checks."""

from __future__ import annotations

import copy
from collections.abc import Iterable

from sentinel_merchant_inbox.contracts import ExceptionItem, ExceptionKind, ExceptionStatus
from sentinel_merchant_inbox.domain import rules


class MemoryInboxStore:
    def __init__(self, items: Iterable[ExceptionItem] | None = None) -> None:
        self._items: dict[tuple[str, str], ExceptionItem] = {}
        for item in items or ():
            self.save_item(item)

    def list_items(
        self,
        *,
        tenant_id: str,
        merchant_ref: str,
        kind: ExceptionKind | None = None,
        status: ExceptionStatus | None = None,
    ) -> list[ExceptionItem]:
        out: list[ExceptionItem] = []
        for item in self._items.values():
            if item.tenant_id != tenant_id or item.merchant_ref != merchant_ref:
                continue
            if not rules.matches_filters(item, kind=kind, status=status):
                continue
            out.append(copy.deepcopy(item))
        out.sort(key=lambda i: i.item_id)
        return out

    def get_item(self, *, tenant_id: str, item_id: str) -> ExceptionItem | None:
        item = self._items.get((tenant_id, item_id))
        return copy.deepcopy(item) if item is not None else None

    def save_item(self, item: ExceptionItem) -> ExceptionItem:
        stored = copy.deepcopy(item)
        self._items[(item.tenant_id, item.item_id)] = stored
        return copy.deepcopy(stored)
