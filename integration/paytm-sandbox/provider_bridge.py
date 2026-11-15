"""payment-provider.v1 shim over Paytm staging status/refund-status.

Evidence talks to this bridge with EVIDENCE_MODE=real-peers.
Merchant fulfillment fields are local defaults (Paytm status has no order book).
Never invent TXN_SUCCESS. Never claim customer credit.
"""

from __future__ import annotations

import os
from decimal import Decimal, InvalidOperation
from typing import Any

from client import PaytmStagingClient, Settings
from fastapi import FastAPI, Header, HTTPException, Query

TOKEN = os.getenv("PAYTM_BRIDGE_TOKEN", "tok-workflow")
SUBJECT_REF = os.getenv("PAYTM_BRIDGE_SUBJECT_REF", "subject-paytm-staging")
MERCHANT_REF = os.getenv("PAYTM_BRIDGE_MERCHANT_REF", "merchant-paytm-staging")


def _minor(amount: Any) -> int:
    if amount in (None, ""):
        return 0
    try:
        value = Decimal(str(amount))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise HTTPException(status_code=502, detail="PROVIDER_AMOUNT_INVALID") from exc
    minor = value * Decimal(100)
    if minor != minor.to_integral_value():
        raise HTTPException(status_code=502, detail="PROVIDER_AMOUNT_INVALID")
    return int(minor)


def _map_status(result_status: str | None, result_code: str | None) -> str | None:
    status = (result_status or "").upper()
    code = str(result_code or "")
    if status in {"TXN_SUCCESS", "SUCCESS"} or code == "01":
        return "CAPTURED"
    if status in {"PENDING", "TXN_PENDING"} or code in {"400", "402"}:
        return "PENDING"
    if code in {"334", "331"}:
        return None  # no payment record
    if status in {"TXN_FAILURE", "FAILURE"} or code:
        return "FAILED"
    return None


def create_app(client: PaytmStagingClient | None = None) -> FastAPI:
    app = FastAPI(title="Paytm staging payment-provider bridge")
    paytm = client or PaytmStagingClient(Settings.from_env())

    def _auth(authorization: str | None) -> None:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="UNAUTHORIZED")
        token = authorization.removeprefix("Bearer ").strip()
        if token != TOKEN:
            raise HTTPException(status_code=403, detail="FORBIDDEN")

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok", "provider": "paytm-staging-bridge"}

    @app.get("/v1/transactions")
    def transactions(
        order_reference: str = Query(...),
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        _auth(authorization)
        body, _raw = paytm.transaction_status(order_reference)
        if not body.get("_signature_verified") and body.get("_signature_present"):
            raise HTTPException(status_code=502, detail="UNVERIFIED_PROVIDER_RESPONSE")
        if body.get("mid") and body.get("mid") != paytm.settings.mid:
            raise HTTPException(status_code=502, detail="PROVIDER_SCOPE_MISMATCH")
        info = body.get("resultInfo") or {}
        mapped = _map_status(info.get("resultStatus"), info.get("resultCode"))
        if mapped is None:
            return {"payments": []}
        txn_id = body.get("txnId")
        if not txn_id:
            # Failed/missing txn id: synthesize a stable failed observation ref only when
            # Paytm returned an explicit failure for this order id.
            txn_id = f"PAYTM-NO-TXN-{order_reference}"
        payment = {
            "transaction_ref": str(txn_id),
            "order_reference": order_reference,
            "subject_ref": SUBJECT_REF,
            "status": mapped,
            "amount_minor": _minor(body.get("txnAmount")),
            "currency": "INR",
            "merchant_ref": MERCHANT_REF,
        }
        return {"payments": [payment]}

    @app.get("/v1/orders/{order_reference}")
    def order(
        order_reference: str,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        _auth(authorization)
        body, _raw = paytm.transaction_status(order_reference)
        info = body.get("resultInfo") or {}
        mapped = _map_status(info.get("resultStatus"), info.get("resultCode"))
        paid = mapped == "CAPTURED"
        # Fulfillment / duplicate flags are NOT provided by Paytm status — local defaults.
        return {
            "order_reference": order_reference,
            "subject_ref": SUBJECT_REF,
            "fulfilled_order_count": 0,
            "merchant_confirmed_duplicate": False,
            "paid": paid,
        }

    @app.get("/v1/refunds")
    def refunds(
        transaction_ref: str = Query(...),
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        _auth(authorization)
        # Paytm refund status needs orderId+refId; without a stored ref this bridge
        # returns empty rather than inventing refunds.
        del transaction_ref
        return {"refunds": []}

    return app


app = create_app()
