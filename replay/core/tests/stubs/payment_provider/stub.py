from __future__ import annotations

import json
from pathlib import Path

CASES = ("valid", "unavailable", "malformed", "unauthorized_or_out_of_scope")
_DIR = Path(__file__).resolve().parent


def load_case(name: str) -> dict:
    if name not in CASES:
        raise KeyError(name)
    return json.loads((_DIR / f"{name}.json").read_text(encoding="utf-8"))


class PaymentProviderStub:
    """In-process payment-provider.v1 double. Never performs live refunds."""

    def __init__(self, case: str = "valid") -> None:
        self.case = case
        self._payload = load_case(case)

    def capabilities(self) -> dict:
        if self.case == "unavailable":
            raise RuntimeError(self._payload["error"]["message"])
        if self.case == "unauthorized_or_out_of_scope":
            raise PermissionError(self._payload["error"]["message"])
        return self._payload["capabilities"]

    def get_transactions(self, order_reference: str) -> dict:
        del order_reference
        if self.case == "unavailable":
            raise RuntimeError(self._payload["error"]["message"])
        if self.case == "unauthorized_or_out_of_scope":
            raise PermissionError(self._payload["error"]["message"])
        return self._payload["transactions_response"]

    def create_refund(self, body: dict, idempotency_key: str) -> dict:
        del body, idempotency_key
        if self.case == "unavailable":
            raise RuntimeError(self._payload["error"]["message"])
        if self.case == "unauthorized_or_out_of_scope":
            raise PermissionError(self._payload["error"]["message"])
        return self._payload["refund_response"]
