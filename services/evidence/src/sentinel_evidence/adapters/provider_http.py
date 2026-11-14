"""Real-peer payment-provider.v1 HTTP adapter. Fail closed; never fall back to fixtures."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote

import httpx

from ..application.errors import (
    ConfigurationError,
    PeerMalformedError,
    PeerUnauthorizedError,
    PeerUnavailableError,
)
from ..domain.digest import canonical_json_bytes
from ..domain.types import Order, Payment, Principal, ProviderSnapshot, Refund


class HttpPaymentProvider:
    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        ttl_seconds: int = 3600,
        client: httpx.Client | None = None,
    ):
        if not base_url.strip():
            raise ConfigurationError("PAYMENT_PROVIDER_BASE_URL is required in real-peers mode")
        if not token.strip():
            raise ConfigurationError("PAYMENT_PROVIDER_TOKEN is required in real-peers mode")
        self._base = base_url.rstrip("/")
        self._token = token
        self._ttl = ttl_seconds
        self._client = client or httpx.Client(timeout=10.0)

    def fetch_snapshot(self, *, order_reference: str, principal: Principal) -> ProviderSnapshot:
        del principal  # provider authorizes via bearer token scope, not forwarded identity headers
        # Caller (collect) already derived the bare provider key from any authorized form.
        encoded = quote(order_reference, safe="")
        payments_body, payments_raw = self._get_json(f"/v1/transactions?order_reference={encoded}")
        order_body, order_raw = self._get_json(f"/v1/orders/{encoded}")
        try:
            payments = tuple(_parse_payment(item) for item in payments_body["payments"])
            order = _parse_order(order_body)
        except (KeyError, TypeError, ValueError) as exc:
            raise PeerMalformedError("Provider response failed schema validation") from exc

        refund_items: list[tuple[bytes, Refund]] = []
        for payment in payments:
            refunds_body, _ = self._get_json(
                f"/v1/refunds?transaction_ref={payment.transaction_ref}"
            )
            try:
                for item in refunds_body["refunds"]:
                    refund = _parse_refund(item)
                    refund_items.append((canonical_json_bytes(_refund_wire(refund)), refund))
            except (KeyError, TypeError, ValueError) as exc:
                raise PeerMalformedError(
                    "Provider refund response failed schema validation"
                ) from exc

        now = datetime.now(UTC)
        observed = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        expires = (now + timedelta(seconds=self._ttl)).strftime("%Y-%m-%dT%H:%M:%SZ")
        payment_items = tuple((canonical_json_bytes(_payment_wire(p)), p) for p in payments)
        # Retain original order bytes; rebuild payment item digests from parsed wire fields.
        del payments_raw
        return ProviderSnapshot(
            payment_items=payment_items,
            order_payload=order_raw,
            order=order,
            refund_items=tuple(refund_items),
            observed_at=observed,
            expires_at=expires,
        )

    def _get_json(self, path: str) -> tuple[Any, bytes]:
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
        if response.status_code == 404:
            raise PeerMalformedError("Provider resource missing or malformed")
        if response.status_code != 200:
            raise PeerMalformedError("Provider returned unexpected status")
        raw = response.content
        try:
            body = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PeerMalformedError("Provider response was not valid JSON") from exc
        return body, raw


def _parse_payment(item: dict) -> Payment:
    return Payment(
        transaction_ref=str(item["transaction_ref"]),
        order_reference=str(item["order_reference"]),
        subject_ref=str(item["subject_ref"]),
        status=item["status"],
        amount_minor=int(item["amount_minor"]),
        currency=item["currency"],
    )


def _parse_order(item: dict) -> Order:
    return Order(
        order_reference=str(item["order_reference"]),
        subject_ref=str(item["subject_ref"]),
        fulfilled_order_count=int(item["fulfilled_order_count"]),
        merchant_confirmed_duplicate=bool(item["merchant_confirmed_duplicate"]),
        paid=bool(item["paid"]),
    )


def _parse_refund(item: dict) -> Refund:
    return Refund(
        action_id=str(item["action_id"]),
        provider_ref=str(item["provider_ref"]),
        transaction_ref=str(item["transaction_ref"]),
        amount_minor=int(item["amount_minor"]),
        currency=item["currency"],
        status=item["status"],
    )


def _payment_wire(payment: Payment) -> dict:
    return {
        "transaction_ref": payment.transaction_ref,
        "order_reference": payment.order_reference,
        "subject_ref": payment.subject_ref,
        "status": payment.status,
        "amount_minor": payment.amount_minor,
        "currency": payment.currency,
    }


def _refund_wire(refund: Refund) -> dict:
    return {
        "action_id": refund.action_id,
        "provider_ref": refund.provider_ref,
        "transaction_ref": refund.transaction_ref,
        "amount_minor": refund.amount_minor,
        "currency": refund.currency,
        "status": refund.status,
    }
