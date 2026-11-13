"""Domain reconciliation covers every finding kind with deterministic fixtures."""

from __future__ import annotations

from sentinel_merchant_settlement.adapters.evidence_stub import StubEvidence, demo_evidence
from sentinel_merchant_settlement.adapters.provider_stub import StubPaymentProvider, demo_payments
from sentinel_merchant_settlement.domain.reconcile import canonical_batch_digest, reconcile
from sentinel_merchant_settlement.domain.types import PeerWorld, SettlementBatch, SettlementRow


def _batch(rows: list[SettlementRow], batch_id: str = "batch-x") -> SettlementBatch:
    return SettlementBatch(
        batch_id=batch_id,
        tenant_id="demo-tenant-a",
        merchant_ref="demo-merchant-1",
        period_start="2026-11-01T00:00:00Z",
        period_end="2026-11-30T23:59:59Z",
        currency="INR",
        rows=tuple(rows),
        source_digest=canonical_batch_digest(rows),
    )


def test_all_finding_kinds_from_fixture_world():
    provider = StubPaymentProvider()
    evidence = StubEvidence()
    world = PeerWorld(
        payments=provider.payments,
        orders=provider.orders,
        evidence=evidence.evidence,
    )
    rows = [
        SettlementRow("row-ok", "TXN-OK", 145000, 5000, "2026-11-02T10:00:00Z", "ORDER-OK"),
        SettlementRow("row-fee", "TXN-FEE", 141000, 9000, "2026-11-02T11:00:00Z", "ORDER-FEE"),
        SettlementRow(
            "row-short", "TXN-SHORT", 100000, 5000, "2026-11-02T12:00:00Z", "ORDER-SHORT"
        ),
        SettlementRow("row-dup-a", "TXN-DUP", 49500, 500, "2026-11-02T13:00:00Z", "ORDER-DUP"),
        SettlementRow("row-dup-b", "TXN-DUP", 49500, 500, "2026-11-02T13:01:00Z", "ORDER-DUP"),
        SettlementRow("row-ghost", "TXN-GHOST", 1000, 0, "2026-11-02T15:00:00Z", "ORDER-GHOST"),
        SettlementRow(
            "row-unmatched",
            "TXN-UNMATCHED",
            19800,
            200,
            "2026-11-02T14:00:00Z",
            "ORDER-FAKE",
        ),
    ]
    findings = reconcile(_batch(rows), world)
    kinds = {f.kind for f in findings}
    assert kinds == {
        "MISSING_PAYMENT",
        "MISSING_SETTLEMENT",
        "DUPLICATE_ROW",
        "FEE_DIFF",
        "SHORT_SETTLE",
        "UNMATCHED_ORDER",
    }
    fee = next(f for f in findings if f.kind == "FEE_DIFF")
    assert fee.expected_minor == 5000
    assert fee.observed_minor == 9000
    assert "evidence-txn-fee" in fee.evidence_ids
    short = next(f for f in findings if f.kind == "SHORT_SETTLE")
    assert short.expected_minor == 145000
    assert short.observed_minor == 100000
    missing_settle = next(f for f in findings if f.kind == "MISSING_SETTLEMENT")
    assert missing_settle.transaction_ref == "TXN-MISS-SETTLE"


def test_clean_match_emits_no_findings_for_matched_payment():
    world = PeerWorld(
        payments=demo_payments()[:1],
        orders=StubPaymentProvider().orders[:1],
        evidence=demo_evidence()[:1],
    )
    rows = [
        SettlementRow("row-ok", "TXN-OK", 145000, 5000, "2026-11-02T10:00:00Z", "ORDER-OK"),
    ]
    findings = reconcile(_batch(rows, "batch-clean"), world)
    assert findings == []


def test_digest_is_stable():
    rows = [
        SettlementRow("row-ok", "TXN-OK", 145000, 5000, "2026-11-02T10:00:00Z", "ORDER-OK"),
    ]
    assert canonical_batch_digest(rows) == canonical_batch_digest(list(rows))
