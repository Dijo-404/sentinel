"""Real PostgreSQL retention of original payload bytes and digests."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import text

from sentinel_evidence.adapters.clock import FixedClock
from sentinel_evidence.adapters.provider_stub import StubPaymentProvider
from sentinel_evidence.adapters.storage_postgres import PostgresEvidenceStore
from sentinel_evidence.application.collect import CollectEvidence, ListEvidence
from sentinel_evidence.domain.types import CollectRequest
from tests.conftest import WORKFLOW


def test_postgres_roundtrip_retains_payload_and_digest(postgres):
    store = PostgresEvidenceStore(postgres, schema="evidence")
    store.migrate()
    clock = FixedClock(datetime(2026, 11, 13, 12, 30, tzinfo=UTC))
    collect = CollectEvidence(StubPaymentProvider(), store, clock)
    listed = ListEvidence(store)
    authorized = "subject-a/DEMO-ORDER-42"
    bundle = collect(
        WORKFLOW,
        CollectRequest("case-demo-42", 1, authorized),
    )
    loaded = listed(WORKFLOW, "case-demo-42")
    assert loaded.case_id == bundle.case_id
    assert loaded.reconciliation_codes == bundle.reconciliation_codes
    assert len(loaded.evidence) == len(bundle.evidence)
    by_id = {item.evidence_id: item for item in loaded.evidence}
    for original in bundle.evidence:
        stored = by_id[original.evidence_id]
        assert stored.digest == original.digest
        assert stored.payload_utf8 == original.payload_utf8
        assert stored.facts == original.facts
    # Bundle row keeps authorized case identity; provider was queried with bare id.
    with postgres.begin() as connection:
        row = connection.execute(
            text("SELECT order_reference FROM evidence.evidence_bundles WHERE case_id = :case_id"),
            {"case_id": "case-demo-42"},
        ).one()
    assert row.order_reference == authorized
