"""Deterministic settlement ↔ payment/order discrepancy rules."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict

from sentinel_merchant_settlement.domain.types import (
    PeerWorld,
    SettlementBatch,
    SettlementFinding,
    SettlementRow,
)


def canonical_batch_digest(rows: tuple[SettlementRow, ...] | list[SettlementRow]) -> str:
    payload = [
        {
            "fee_minor": row.fee_minor,
            "occurred_at": row.occurred_at,
            "order_ref": row.order_ref,
            "row_id": row.row_id,
            "settled_minor": row.settled_minor,
            "transaction_ref": row.transaction_ref,
        }
        for row in rows
    ]
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def reconcile(batch: SettlementBatch, world: PeerWorld) -> list[SettlementFinding]:
    """Emit discrepancy findings. Does not mutate peers or external ledgers."""
    findings: list[SettlementFinding] = []
    payments = world.payment_by_ref()
    orders = world.order_by_ref()
    seq = 0

    def next_id(kind: str) -> str:
        nonlocal seq
        seq += 1
        return f"finding-{batch.batch_id}-{kind.lower()}-{seq}"

    by_txn: dict[str, list[SettlementRow]] = defaultdict(list)
    for row in batch.rows:
        by_txn[row.transaction_ref].append(row)

    settled_refs: set[str] = set()
    for txn_ref, group in by_txn.items():
        if len(group) > 1:
            findings.append(
                SettlementFinding(
                    finding_id=next_id("DUPLICATE_ROW"),
                    batch_id=batch.batch_id,
                    kind="DUPLICATE_ROW",
                    transaction_ref=txn_ref,
                    observed_minor=len(group),
                    evidence_ids=[],
                )
            )
            continue

        row = group[0]
        settled_refs.add(txn_ref)
        payment = payments.get(txn_ref)
        evidence_ids = world.evidence_ids_for(
            transaction_ref=txn_ref, order_reference=row.order_ref
        )

        if payment is None:
            findings.append(
                SettlementFinding(
                    finding_id=next_id("MISSING_PAYMENT"),
                    batch_id=batch.batch_id,
                    kind="MISSING_PAYMENT",
                    transaction_ref=txn_ref,
                    observed_minor=row.settled_minor,
                    evidence_ids=evidence_ids,
                )
            )
            continue

        if payment.currency != batch.currency:
            findings.append(
                SettlementFinding(
                    finding_id=next_id("MISSING_PAYMENT"),
                    batch_id=batch.batch_id,
                    kind="MISSING_PAYMENT",
                    transaction_ref=txn_ref,
                    expected_minor=payment.amount_minor,
                    observed_minor=row.settled_minor,
                    evidence_ids=evidence_ids,
                )
            )
            continue

        if row.fee_minor != payment.expected_fee_minor:
            findings.append(
                SettlementFinding(
                    finding_id=next_id("FEE_DIFF"),
                    batch_id=batch.batch_id,
                    kind="FEE_DIFF",
                    transaction_ref=txn_ref,
                    expected_minor=payment.expected_fee_minor,
                    observed_minor=row.fee_minor,
                    evidence_ids=evidence_ids,
                )
            )

        expected_net = payment.amount_minor - row.fee_minor
        if row.settled_minor < expected_net:
            findings.append(
                SettlementFinding(
                    finding_id=next_id("SHORT_SETTLE"),
                    batch_id=batch.batch_id,
                    kind="SHORT_SETTLE",
                    transaction_ref=txn_ref,
                    expected_minor=expected_net,
                    observed_minor=row.settled_minor,
                    evidence_ids=evidence_ids,
                )
            )

        if row.order_ref is not None:
            order = orders.get(row.order_ref)
            if order is None or payment.order_reference != row.order_ref:
                findings.append(
                    SettlementFinding(
                        finding_id=next_id("UNMATCHED_ORDER"),
                        batch_id=batch.batch_id,
                        kind="UNMATCHED_ORDER",
                        transaction_ref=txn_ref,
                        evidence_ids=world.evidence_ids_for(order_reference=row.order_ref),
                    )
                )

    for payment in world.payments:
        if payment.status != "CAPTURED":
            continue
        if payment.currency != batch.currency:
            continue
        if payment.occurred_at < batch.period_start or payment.occurred_at > batch.period_end:
            continue
        if payment.transaction_ref in settled_refs:
            continue
        if payment.transaction_ref in by_txn and len(by_txn[payment.transaction_ref]) > 1:
            continue
        findings.append(
            SettlementFinding(
                finding_id=next_id("MISSING_SETTLEMENT"),
                batch_id=batch.batch_id,
                kind="MISSING_SETTLEMENT",
                transaction_ref=payment.transaction_ref,
                expected_minor=payment.amount_minor,
                evidence_ids=world.evidence_ids_for(
                    transaction_ref=payment.transaction_ref,
                    order_reference=payment.order_reference,
                ),
            )
        )

    return findings
