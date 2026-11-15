"""Capture Paytm staging observations, redact, and write Sentinel fixtures."""

from __future__ import annotations

import argparse
import hashlib
import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from client import PaytmStagingClient, Settings

ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / ".raw"
FIXTURES_DIR = ROOT / "fixtures"
NORMALIZED_DIR = ROOT / "normalized"


def inr_to_minor(value: str | int | float | Decimal) -> int:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("Invalid monetary value") from exc
    if not amount.is_finite() or amount < 0:
        raise ValueError("Invalid monetary value")
    minor = amount * Decimal(100)
    if minor != minor.to_integral_value():
        raise ValueError("Amount has sub-paise precision")
    return int(minor)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _map_payment_status(result_status: str | None, result_code: str | None) -> str:
    status = (result_status or "").upper()
    if status in {"TXN_SUCCESS", "SUCCESS"} or result_code == "01":
        return "CAPTURED"
    if status in {"PENDING", "TXN_PENDING"} or result_code in {"400", "402"}:
        return "PENDING"
    return "FAILED"


def _map_refund_status(body: dict[str, Any]) -> str:
    info = body.get("resultInfo") or {}
    status = str(info.get("resultStatus") or body.get("acceptRefundStatus") or "").upper()
    if status in {"TXN_SUCCESS", "SUCCESS", "PENDING"}:
        # Provider acceptance / pending is never final customer credit.
        return "PENDING"
    if "FAIL" in status or status in {"TXN_FAILURE"}:
        return "FAILED_FINAL"
    return "PENDING"


def normalize_payment(
    *,
    body: dict[str, Any],
    raw: bytes,
    fixture_id: str,
    evidence_mode: str,
) -> dict[str, Any]:
    info = body.get("resultInfo") or {}
    amount = body.get("txnAmount")
    amount_minor = None
    if amount is not None and amount != "":
        amount_minor = inr_to_minor(amount)
    normalized_status = _map_payment_status(info.get("resultStatus"), info.get("resultCode"))
    txn_id = body.get("txnId") or f"NONE-{fixture_id}"
    order_id = body.get("orderId") or "UNKNOWN"
    return {
        "fixture_id": fixture_id,
        "source": "paytm_staging",
        "provider": "paytm",
        "environment": "staging",
        "evidence_mode": evidence_mode,
        "original_signature_verified": bool(body.get("_signature_verified")),
        "redacted": True,
        "replay_only": evidence_mode.endswith("replay"),
        "observed_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "raw_sha256": _sha256(raw),
        "provider_result": {
            "result_status": info.get("resultStatus"),
            "result_code": info.get("resultCode"),
            "result_msg": info.get("resultMsg"),
        },
        "payment": {
            "transaction_ref": str(txn_id),
            "order_ref": str(order_id),
            "amount_minor": amount_minor,
            "currency": "INR",
            "provider_status": info.get("resultStatus"),
            "provider_result_code": info.get("resultCode"),
            "normalized_status": normalized_status,
            "payment_mode": body.get("paymentMode"),
            "merchant_ref": body.get("mid") or Settings.from_env().mid,
        },
        "sentinel_payment": {
            "transaction_ref": str(txn_id),
            "order_reference": str(order_id),
            "subject_ref": "subject-paytm-staging",
            "status": normalized_status,
            "amount_minor": amount_minor if amount_minor is not None else 0,
            "currency": "INR",
            "merchant_ref": "merchant-paytm-staging",
        },
    }


def normalize_refund(
    *,
    body: dict[str, Any],
    raw: bytes,
    fixture_id: str,
    evidence_mode: str,
) -> dict[str, Any]:
    info = body.get("resultInfo") or {}
    amount = body.get("refundAmount")
    amount_minor = inr_to_minor(amount) if amount not in (None, "") else None
    return {
        "fixture_id": fixture_id,
        "source": "paytm_staging",
        "provider": "paytm",
        "environment": "staging",
        "evidence_mode": evidence_mode,
        "original_signature_verified": bool(body.get("_signature_verified")),
        "redacted": True,
        "replay_only": True,
        "observed_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "raw_sha256": _sha256(raw),
        "provider_result": {
            "result_status": info.get("resultStatus"),
            "result_code": info.get("resultCode"),
            "result_msg": info.get("resultMsg"),
        },
        "refund": {
            "provider_ref": body.get("refId") or body.get("refundId") or fixture_id,
            "transaction_ref": body.get("txnId"),
            "order_ref": body.get("orderId"),
            "amount_minor": amount_minor,
            "currency": "INR",
            "normalized_status": _map_refund_status(body),
            "accept_refund_status": body.get("acceptRefundStatus"),
            "refund_id": body.get("refundId"),
        },
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def capture_status(order_id: str, *, label: str | None = None) -> dict[str, Any]:
    client = PaytmStagingClient()
    body, raw = client.transaction_status(order_id)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    fixture_id = label or f"status-{order_id}-{stamp}"
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / f"{fixture_id}.json").write_bytes(raw)
    info = body.get("resultInfo") or {}
    mode = (
        "paytm-staging-live"
        if body.get("_signature_verified")
        else "paytm-staging-unverified"
    )
    # Successful captures are replay fixtures once saved.
    if str(info.get("resultStatus") or "").upper() == "TXN_SUCCESS":
        mode = "paytm-staging-replay"
    normalized = normalize_payment(body=body, raw=raw, fixture_id=fixture_id, evidence_mode=mode)
    _write_json(FIXTURES_DIR / f"{fixture_id}.json", normalized)
    return normalized


def capture_initiate(amount: str = "10.00") -> dict[str, Any]:
    client = PaytmStagingClient()
    order_id = f"SENTINEL-{uuid.uuid4().hex[:12]}"
    body, raw = client.initiate_payment(order_id=order_id, amount=amount)
    fixture_id = f"initiate-{order_id}"
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / f"{fixture_id}.json").write_bytes(raw)
    payload = {
        "fixture_id": fixture_id,
        "source": "paytm_staging",
        "environment": "staging",
        "evidence_mode": "paytm-staging-live",
        "order_id": order_id,
        "amount": amount,
        "original_signature_verified": bool(body.get("_signature_verified")),
        "provider_result": body.get("resultInfo"),
        "txn_token_present": bool(body.get("txnToken")),
        "raw_sha256": _sha256(raw),
    }
    _write_json(FIXTURES_DIR / f"{fixture_id}.json", payload)
    return payload


def capture_refund_apply(
    *, order_id: str, txn_id: str, refund_amount: str, ref_id: str | None = None
) -> dict[str, Any]:
    client = PaytmStagingClient()
    ref = ref_id or f"SNT-REF-{uuid.uuid4().hex[:10]}"
    body, raw = client.refund_apply(
        order_id=order_id, txn_id=txn_id, ref_id=ref, refund_amount=refund_amount
    )
    fixture_id = f"refund-apply-{ref}"
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / f"{fixture_id}.json").write_bytes(raw)
    normalized = normalize_refund(
        body={**body, "refId": body.get("refId") or ref, "orderId": order_id, "txnId": txn_id},
        raw=raw,
        fixture_id=fixture_id,
        evidence_mode="paytm-staging-replay",
    )
    _write_json(FIXTURES_DIR / f"{fixture_id}.json", normalized)
    return normalized


def capture_refund_status(*, order_id: str, ref_id: str) -> dict[str, Any]:
    client = PaytmStagingClient()
    body, raw = client.refund_status(order_id=order_id, ref_id=ref_id)
    fixture_id = f"refund-status-{ref_id}"
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / f"{fixture_id}.json").write_bytes(raw)
    normalized = normalize_refund(
        body={**body, "refId": body.get("refId") or ref_id, "orderId": order_id},
        raw=raw,
        fixture_id=fixture_id,
        evidence_mode="paytm-staging-replay",
    )
    _write_json(FIXTURES_DIR / f"{fixture_id}.json", normalized)
    return normalized


def build_manifest() -> dict[str, Any]:
    fixtures = sorted(FIXTURES_DIR.glob("*.json")) if FIXTURES_DIR.exists() else []
    entries = []
    payments: list[dict[str, Any]] = []
    refunds: list[dict[str, Any]] = []
    for path in fixtures:
        payload = json.loads(path.read_text(encoding="utf-8"))
        digest = _sha256(path.read_bytes())
        entries.append(
            {
                "path": str(path.relative_to(ROOT)),
                "fixture_id": payload.get("fixture_id"),
                "evidence_mode": payload.get("evidence_mode"),
                "sha256": digest,
            }
        )
        if "sentinel_payment" in payload:
            payments.append(payload["sentinel_payment"])
        if "refund" in payload:
            refunds.append(payload["refund"])
    manifest = {
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fixture_count": len(entries),
        "fixtures": entries,
        "note": (
            "Replay fixtures are not fresh evidence. Live staging writes require an "
            "initiate-capable test MID; shared demo MID may only support status reads."
        ),
    }
    NORMALIZED_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(NORMALIZED_DIR / "manifest.json", manifest)
    _write_json(NORMALIZED_DIR / "payments.json", {"payments": payments})
    _write_json(NORMALIZED_DIR / "refunds.json", {"refunds": refunds})
    return manifest


def probe_capabilities() -> dict[str, Any]:
    client = PaytmStagingClient()
    probe_order = f"SENTINEL-PROBE-{uuid.uuid4().hex[:8]}"
    status_body, _ = client.transaction_status(probe_order)
    init_body, _ = client.initiate_payment(order_id=probe_order, amount="1.00")
    refund_body, _ = client.refund_apply(
        order_id="NOPE",
        txn_id="NOPE",
        ref_id=f"SNT-PROBE-{uuid.uuid4().hex[:6]}",
        refund_amount="1.00",
    )
    result = {
        "mid": client.settings.mid,
        "status_api": status_body.get("resultInfo"),
        "status_signature_verified": status_body.get("_signature_verified"),
        "initiate_api": init_body.get("resultInfo"),
        "refund_api": refund_body.get("resultInfo"),
        "can_status": True,
        "can_initiate": bool(init_body.get("txnToken")),
        "can_refund": str((refund_body.get("resultInfo") or {}).get("resultCode"))
        not in {"335", "501"},
    }
    _write_json(FIXTURES_DIR / "capabilities.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture Paytm staging observations")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("probe", help="Probe status/initiate/refund capabilities")
    p_status = sub.add_parser("status", help="Capture transaction status")
    p_status.add_argument("order_id")
    p_status.add_argument("--label")
    p_init = sub.add_parser("initiate", help="Attempt payment initiation")
    p_init.add_argument("--amount", default="10.00")
    p_refund = sub.add_parser("refund-apply", help="Attempt refund apply")
    p_refund.add_argument("--order-id", required=True)
    p_refund.add_argument("--txn-id", required=True)
    p_refund.add_argument("--amount", required=True)
    p_refund.add_argument("--ref-id")
    p_rstat = sub.add_parser("refund-status", help="Capture refund status")
    p_rstat.add_argument("--order-id", required=True)
    p_rstat.add_argument("--ref-id", required=True)
    sub.add_parser("manifest", help="Rebuild normalized manifest")
    p_batch = sub.add_parser(
        "batch-status",
        help="Capture status for several order IDs (failed/missing look-ups included)",
    )
    p_batch.add_argument("order_ids", nargs="+")

    args = parser.parse_args()
    if args.cmd == "probe":
        print(json.dumps(probe_capabilities(), indent=2))
    elif args.cmd == "status":
        print(json.dumps(capture_status(args.order_id, label=args.label), indent=2))
    elif args.cmd == "initiate":
        print(json.dumps(capture_initiate(args.amount), indent=2))
    elif args.cmd == "refund-apply":
        print(
            json.dumps(
                capture_refund_apply(
                    order_id=args.order_id,
                    txn_id=args.txn_id,
                    refund_amount=args.amount,
                    ref_id=args.ref_id,
                ),
                indent=2,
            )
        )
    elif args.cmd == "refund-status":
        print(
            json.dumps(
                capture_refund_status(order_id=args.order_id, ref_id=args.ref_id),
                indent=2,
            )
        )
    elif args.cmd == "batch-status":
        out = [capture_status(oid) for oid in args.order_ids]
        build_manifest()
        print(json.dumps(out, indent=2))
    elif args.cmd == "manifest":
        print(json.dumps(build_manifest(), indent=2))


if __name__ == "__main__":
    main()
