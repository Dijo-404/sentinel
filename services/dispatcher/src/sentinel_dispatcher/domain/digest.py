"""Canonical refund-action digest matching the pinned contract baseline."""

from __future__ import annotations

import json
from collections.abc import Mapping
from hashlib import sha256
from typing import Any

REFUND_KEYS = (
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


def _reject_non_schema(payload: Mapping[str, Any]) -> dict[str, Any]:
    if set(payload) != set(REFUND_KEYS):
        raise ValueError("INVALID_PAYLOAD_FIELDS")
    if payload["action"] != "REQUEST_REFUND":
        raise ValueError("UNSUPPORTED_ACTION")
    if not isinstance(payload["amount_minor"], int) or isinstance(payload["amount_minor"], bool):
        raise ValueError("INVALID_AMOUNT")
    if payload["amount_minor"] <= 0:
        raise ValueError("INVALID_AMOUNT")
    if payload["currency"] != "INR":
        raise ValueError("INVALID_CURRENCY")
    if payload["destination"] != "ORIGINAL_PAYMENT_ROUTE":
        raise ValueError("INVALID_DESTINATION")
    if not isinstance(payload["case_revision"], int) or isinstance(payload["case_revision"], bool):
        raise ValueError("INVALID_CASE_REVISION")
    if payload["case_revision"] <= 0:
        raise ValueError("INVALID_CASE_REVISION")
    evidence_ids = payload["evidence_ids"]
    if not isinstance(evidence_ids, list) or not evidence_ids:
        raise ValueError("INVALID_EVIDENCE_IDS")
    if any(not isinstance(item, str) or not item for item in evidence_ids):
        raise ValueError("INVALID_EVIDENCE_IDS")
    for key in ("case_id", "transaction_ref", "policy_version"):
        if not isinstance(payload[key], str) or not payload[key]:
            raise ValueError("INVALID_PAYLOAD_STRING")
    return {key: payload[key] for key in REFUND_KEYS}


def canonical_action(payload: Mapping[str, Any]) -> bytes:
    cleaned = _reject_non_schema(payload)
    return json.dumps(
        cleaned,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def action_digest(payload: Mapping[str, Any]) -> str:
    return sha256(canonical_action(payload)).hexdigest()
