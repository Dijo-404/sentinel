"""Canonical action digest: SHA-256 of sorted UTF-8 JSON without whitespace."""

from __future__ import annotations

import hashlib
import json
from typing import Any

REFUND_FIELDS = (
    "action",
    "amount_minor",
    "case_id",
    "case_revision",
    "currency",
    "destination",
    "evidence_ids",
    "policy_version",
    "transaction_ref",
)


def canonical_refund_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Reject undeclared fields and normalize types for hashing."""
    extra = set(payload) - set(REFUND_FIELDS)
    if extra:
        raise ValueError(f"Undeclared refund fields: {sorted(extra)}")
    missing = set(REFUND_FIELDS) - set(payload)
    if missing:
        raise ValueError(f"Missing refund fields: {sorted(missing)}")
    if payload["action"] != "REQUEST_REFUND":
        raise ValueError("Only REQUEST_REFUND is accepted on financial ledger routes")
    if not isinstance(payload["case_revision"], int) or payload["case_revision"] < 1:
        raise ValueError("case_revision must be a positive integer")
    if not isinstance(payload["amount_minor"], int) or payload["amount_minor"] < 1:
        raise ValueError("amount_minor must be a positive integer")
    if payload["currency"] != "INR":
        raise ValueError("currency must be INR")
    if payload["destination"] != "ORIGINAL_PAYMENT_ROUTE":
        raise ValueError("destination must be ORIGINAL_PAYMENT_ROUTE")
    evidence_ids = payload["evidence_ids"]
    if not isinstance(evidence_ids, list) or not evidence_ids:
        raise ValueError("evidence_ids must be a nonempty list")
    if any(not isinstance(item, str) or not item for item in evidence_ids):
        raise ValueError("evidence_ids must be nonempty strings")
    for key in ("case_id", "transaction_ref", "policy_version"):
        if not isinstance(payload[key], str) or not payload[key]:
            raise ValueError(f"{key} must be a nonempty string")
    return {key: payload[key] for key in REFUND_FIELDS}


def canonical_bytes(payload: dict[str, Any]) -> bytes:
    normalized = canonical_refund_payload(payload)
    text = json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return text.encode("utf-8")


def action_digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()
