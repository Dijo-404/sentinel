"""Real-peer payment-provider.v1 HTTP adapter. Fail closed; never fall back to fixtures."""

from __future__ import annotations

import json
from typing import Any

import httpx

from sentinel_merchant_settlement.application.errors import (
    ConfigurationError,
    PeerMalformedError,
    PeerUnauthorizedError,
    PeerUnavailableError,
)
from sentinel_merchant_settlement.domain.types import Order, Payment, PeerWorld, Principal


class HttpPaymentProvider:
    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        client: httpx.Client | None = None,
    ) -> None:
        if not base_url.strip():
            raise ConfigurationError("PAYMENT_PROVIDER_BASE_URL is required in real-peers mode")
        if not token.strip():
            raise ConfigurationError("PAYMENT_PROVIDER_TOKEN is required in real-peers mode")
        self._base = base_url.rstrip("/")
        self._token = token
        self._client = client or httpx.Client(timeout=10.0)

    def load_world(
        self,
        *,
        principal: Principal,
        tenant_id: str,
        merchant_ref: str,
        period_start: str,
        period_end: str,
        order_refs: tuple[str, ...],
        transaction_refs: tuple[str, ...],
    ) -> PeerWorld:
        del principal, tenant_id, merchant_ref, period_start, period_end, transaction_refs
        payments: list[Payment] = []
        orders: list[Order] = []
        seen_orders: set[str] = set()
        refs = order_refs or ()
        if not refs:
            # Period catalogue endpoint used by real peers when assembled.
            body = self._get_json("/v1/transactions")
            try:
                for item in body["payments"]:
                    payments.append(_parse_payment(item))
            except (KeyError, TypeError, ValueError) as exc:
                raise PeerMalformedError("Provider response failed schema validation") from exc
            for payment in payments:
                if payment.order_reference not in seen_orders:
                    order_body = self._get_json(f"/v1/orders/{payment.order_reference}")
                    orders.append(_parse_order(order_body))
                    seen_orders.add(payment.order_reference)
            return PeerWorld(payments=tuple(payments), orders=tuple(orders), evidence=())

        for order_reference in refs:
            body = self._get_json(f"/v1/transactions?order_reference={order_reference}")
            try:
                for item in body["payments"]:
                    payments.append(_parse_payment(item))
            except (KeyError, TypeError, ValueError) as exc:
                raise PeerMalformedError("Provider response failed schema validation") from exc
            order_body = self._get_json(f"/v1/orders/{order_reference}")
            try:
                orders.append(_parse_order(order_body))
            except (KeyError, TypeError, ValueError) as exc:
                raise PeerMalformedError("Provider order failed schema validation") from exc
        return PeerWorld(payments=tuple(payments), orders=tuple(orders), evidence=())

    def _get_json(self, path: str) -> Any:
        try:
            response = self._client.get(
                f"{self._base}{path}",
                headers={"Authorization": f"Bearer {self._token}"},
            )
        except httpx.HTTPError as exc:
            raise PeerUnavailableError("Required peer unavailable") from exc
        if response.status_code in {401, 403}:
            raise PeerUnauthorizedError("Provider denied scoped read")
        if response.status_code >= 500:
            raise PeerUnavailableError("Required peer unavailable")
        if response.status_code != 200:
            raise PeerMalformedError("Provider returned unexpected status")
        try:
            return json.loads(response.content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PeerMalformedError("Provider response was not valid JSON") from exc


def _parse_payment(item: dict) -> Payment:
    expected_fee = item.get("expected_fee_minor", 0)
    return Payment(
        transaction_ref=str(item["transaction_ref"]),
        order_reference=str(item["order_reference"]),
        subject_ref=str(item["subject_ref"]),
        status=item["status"],
        amount_minor=int(item["amount_minor"]),
        currency=str(item["currency"]),
        expected_fee_minor=int(expected_fee),
        occurred_at=str(item.get("occurred_at", "2026-11-02T10:00:00Z")),
    )


def _parse_order(item: dict) -> Order:
    return Order(
        order_reference=str(item["order_reference"]),
        subject_ref=str(item["subject_ref"]),
        fulfilled_order_count=int(item["fulfilled_order_count"]),
        merchant_confirmed_duplicate=bool(item["merchant_confirmed_duplicate"]),
        paid=bool(item["paid"]),
    )
