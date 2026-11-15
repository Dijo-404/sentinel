"""Paytm staging client: checksummed status, initiate, and refund calls."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from paytmchecksum import generateSignature, verifySignature


class PaytmStagingError(RuntimeError):
    """Provider rejected or returned an unverifiable response."""


@dataclass(frozen=True)
class Settings:
    mid: str
    key: str
    website: str
    industry_type: str
    channel_id: str
    callback_url: str
    payment_base: str
    refund_base: str

    @classmethod
    def from_env(cls, env_path: Path | None = None) -> Settings:
        if env_path is not None:
            load_dotenv(env_path, override=True)
        else:
            load_dotenv(Path(__file__).resolve().parent / ".env", override=True)
        mid = os.environ["PAYTM_MID"].strip()
        key = os.environ["PAYTM_MERCHANT_KEY"].strip()
        if not mid or not key:
            raise PaytmStagingError("PAYTM_MID and PAYTM_MERCHANT_KEY are required")
        if "#" in key and len(key) < 16:
            raise PaytmStagingError(
                "Merchant key looks truncated; quote PAYTM_MERCHANT_KEY in .env "
                '(keys may contain #)'
            )
        return cls(
            mid=mid,
            key=key,
            website=os.getenv("PAYTM_WEBSITE_NAME", "WEBSTAGING"),
            industry_type=os.getenv("PAYTM_INDUSTRY_TYPE", "Retail"),
            channel_id=os.getenv("PAYTM_CHANNEL_ID", "WEB"),
            callback_url=os.getenv("PAYTM_CALLBACK_URL", "http://localhost:8025/callback"),
            payment_base=os.getenv(
                "PAYTM_PAYMENT_BASE_URL", "https://securestage.paytmpayments.com"
            ).rstrip("/"),
            refund_base=os.getenv(
                "PAYTM_REFUND_BASE_URL", "https://securegw-stage.paytmpayments.in"
            ).rstrip("/"),
        )


def _sign(body: dict[str, Any], key: str) -> dict[str, Any]:
    signature = generateSignature(json.dumps(body), key)
    return {"body": body, "head": {"signature": signature}}


def _verify_body(body: dict[str, Any], key: str, signature: str | None) -> bool:
    if not signature:
        return False
    compact = json.dumps(body, separators=(",", ":"), ensure_ascii=False)
    spaced = json.dumps(body, ensure_ascii=False)
    return verifySignature(compact, key, signature) or verifySignature(spaced, key, signature)


class PaytmStagingClient:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings.from_env()
        self._http = requests.Session()

    def _post(self, url: str, body: dict[str, Any]) -> tuple[dict[str, Any], bytes]:
        payload = _sign(body, self.settings.key)
        response = self._http.post(
            url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=30,
            allow_redirects=False,
        )
        raw = response.content
        try:
            parsed = response.json()
        except ValueError as exc:
            raise PaytmStagingError(f"Non-JSON response from {url}") from exc
        data = parsed.get("body") or {}
        signature = (parsed.get("head") or {}).get("signature")
        verified = _verify_body(data, self.settings.key, signature) if signature else False
        # Some failure bodies omit a signature; keep raw and mark unverified.
        data = dict(data)
        data["_http_status"] = response.status_code
        data["_signature_verified"] = verified
        data["_signature_present"] = bool(signature)
        return data, raw

    def transaction_status(self, order_id: str) -> tuple[dict[str, Any], bytes]:
        return self._post(
            f"{self.settings.payment_base}/v3/order/status",
            {"mid": self.settings.mid, "orderId": order_id},
        )

    def initiate_payment(
        self, *, order_id: str, amount: str = "10.00", cust_id: str = "SENTINEL-TEST-CUSTOMER"
    ) -> tuple[dict[str, Any], bytes]:
        body = {
            "requestType": "Payment",
            "mid": self.settings.mid,
            "websiteName": self.settings.website,
            "orderId": order_id,
            "callbackUrl": self.settings.callback_url,
            "txnAmount": {"value": amount, "currency": "INR"},
            "userInfo": {"custId": cust_id},
        }
        url = (
            f"{self.settings.payment_base}/theia/api/v1/initiateTransaction"
            f"?mid={self.settings.mid}&orderId={order_id}"
        )
        return self._post(url, body)

    def refund_apply(
        self,
        *,
        order_id: str,
        txn_id: str,
        ref_id: str,
        refund_amount: str,
    ) -> tuple[dict[str, Any], bytes]:
        body = {
            "mid": self.settings.mid,
            "txnType": "REFUND",
            "orderId": order_id,
            "txnId": txn_id,
            "refId": ref_id,
            "refundAmount": refund_amount,
        }
        return self._post(f"{self.settings.refund_base}/refund/apply", body)

    def refund_status(self, *, order_id: str, ref_id: str) -> tuple[dict[str, Any], bytes]:
        body = {"mid": self.settings.mid, "orderId": order_id, "refId": ref_id}
        return self._post(f"{self.settings.refund_base}/v2/refund/status", body)
