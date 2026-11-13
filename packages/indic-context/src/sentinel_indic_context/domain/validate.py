"""Structured proposal parsing, ambiguity and safety checks."""

from __future__ import annotations

import re
from typing import Any

from pydantic import ValidationError

from sentinel_indic_context.domain.types import (
    ALLOWED_ACTIONS,
    DisputeAction,
    EscalateAction,
    Evidence,
    ModelRequest,
    RecheckAction,
    RefundAction,
    StatusAction,
    SyncAction,
)

_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.IGNORECASE),
    re.compile(r"\bsystem\s*:\s*", re.IGNORECASE),
    re.compile(r"\byou\s+are\s+now\b.*\badmin\b", re.IGNORECASE),
    re.compile(r"disclose\s+(the\s+)?(api\s+)?key", re.IGNORECASE),
    re.compile(r"<\s*/?\s*system\s*>", re.IGNORECASE),
    re.compile(r"\[INST\]|<<SYS>>", re.IGNORECASE),
]

_ACTION_MODELS = {
    "REQUEST_REFUND": RefundAction,
    "ESCALATE": EscalateAction,
    "STATUS_UPDATE": StatusAction,
    "OPEN_DISPUTE": DisputeAction,
    "SCHEDULE_RECHECK": RecheckAction,
    "SYNC_ORDER": SyncAction,
}


def detect_prompt_injection(*texts: str) -> bool:
    return any(pattern.search(text) for text in texts for pattern in _INJECTION_PATTERNS if text)


def evidence_transaction_refs(evidence: list[Evidence]) -> set[str]:
    refs: set[str] = set()
    for item in evidence:
        facts = item.facts or {}
        payment = facts.get("payment") if isinstance(facts.get("payment"), dict) else None
        refund = facts.get("refund") if isinstance(facts.get("refund"), dict) else None
        if payment and isinstance(payment.get("transaction_ref"), str):
            refs.add(payment["transaction_ref"])
        if refund and isinstance(refund.get("transaction_ref"), str):
            refs.add(refund["transaction_ref"])
        # Allow compact fixture shape: facts.kind + nested fields already covered.
        if facts.get("kind") == "PAYMENT" and isinstance(facts.get("payment"), dict):
            ref = facts["payment"].get("transaction_ref")
            if isinstance(ref, str):
                refs.add(ref)
    return refs


def evidence_ids(evidence: list[Evidence]) -> set[str]:
    return {item.evidence_id for item in evidence}


def parse_proposal(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("MALFORMED_PROPOSAL")
    action = raw.get("action")
    if not isinstance(action, str):
        raise ValueError("MALFORMED_PROPOSAL")
    if action not in ALLOWED_ACTIONS:
        raise ValueError("UNSUPPORTED_ACTION")
    model = _ACTION_MODELS[action]
    try:
        parsed = model.model_validate(raw)
    except ValidationError as exc:
        raise ValueError("MALFORMED_PROPOSAL") from exc
    return parsed.model_dump(exclude_none=True)


def validate_proposal(raw: dict[str, Any] | None, request: ModelRequest) -> list[str]:
    """Return reason codes when a proposal must fail. Empty list means accept."""
    if detect_prompt_injection(
        request.input.original_text,
        *(message.text for message in request.input.messages),
    ):
        return ["PROMPT_INJECTION"]

    if raw is None:
        return ["MALFORMED_PROPOSAL"]

    try:
        proposal = parse_proposal(raw)
    except ValueError as exc:
        code = str(exc)
        if code in {"MALFORMED_PROPOSAL", "UNSUPPORTED_ACTION"}:
            return [code]
        return ["MALFORMED_PROPOSAL"]

    reasons: list[str] = []
    if proposal["case_id"] != request.case.case_id:
        reasons.append("CASE_SCOPE_MISMATCH")
    if proposal["case_revision"] != request.input.case_revision:
        reasons.append("REVISION_MISMATCH")

    known_ids = evidence_ids(request.evidence)
    for eid in proposal.get("evidence_ids") or []:
        if eid not in known_ids:
            reasons.append("HALLUCINATED_EVIDENCE_REF")
            break

    txn = proposal.get("transaction_ref")
    if isinstance(txn, str) and txn:
        known_txns = evidence_transaction_refs(request.evidence)
        if known_txns and txn not in known_txns:
            reasons.append("HALLUCINATED_TRANSACTION_REF")

    return reasons
