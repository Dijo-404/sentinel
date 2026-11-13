"""In-process request store for fixture/local runs."""

from __future__ import annotations

from copy import deepcopy

from sentinel_merchant_refunds.domain.types import MerchantRefundRequest


class MemoryRequestStore:
    def __init__(self) -> None:
        self._by_id: dict[tuple[str, str], MerchantRefundRequest] = {}
        self._by_idem: dict[tuple[str, str], str] = {}

    def put(self, request: MerchantRefundRequest) -> None:
        self._by_id[(request.tenant_id, request.request_id)] = deepcopy(request)

    def get(self, tenant_id: str, request_id: str) -> MerchantRefundRequest | None:
        found = self._by_id.get((tenant_id, request_id))
        return deepcopy(found) if found is not None else None

    def get_by_idempotency(
        self, tenant_id: str, idempotency_key: str
    ) -> MerchantRefundRequest | None:
        request_id = self._by_idem.get((tenant_id, idempotency_key))
        if request_id is None:
            return None
        return self.get(tenant_id, request_id)

    def put_idempotency(
        self, tenant_id: str, idempotency_key: str, request: MerchantRefundRequest
    ) -> None:
        self._by_idem[(tenant_id, idempotency_key)] = request.request_id
        self.put(request)
