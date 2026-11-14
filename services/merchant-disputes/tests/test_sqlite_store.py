"""Durable sqlite dispute store for real-peers."""

from __future__ import annotations

from pathlib import Path

from sentinel_merchant_disputes.adapters.storage_sqlite import SqliteDisputeStore
from sentinel_merchant_disputes.bootstrap import Settings, build_app
from sentinel_merchant_disputes.domain.types import DisputeCase


def test_sqlite_dispute_round_trip(tmp_path: Path):
    store = SqliteDisputeStore(tmp_path / "disputes.db")
    dispute = DisputeCase(
        dispute_id="d-1",
        tenant_id="tenant-demo",
        merchant_ref="merchant-demo",
        case_id="case-demo-42",
        reason_code="CHARGEBACK",
        deadline_at="2026-11-20T00:00:00Z",
        evidence_packet_ids=(),
        status="OPEN",
        order_reference="DEMO-ORDER-42",
        case_revision=1,
    )
    store.create(dispute, idempotency_key="idem-1")
    reopened = SqliteDisputeStore(tmp_path / "disputes.db")
    loaded = reopened.get("d-1")
    assert loaded is not None
    assert loaded.order_reference == "DEMO-ORDER-42"
    again = reopened.create(dispute, idempotency_key="idem-1")
    assert again.dispute_id == "d-1"


def test_real_peers_accepts_database_url(tmp_path: Path):
    app = build_app(
        Settings(
            mode="real-peers",
            tokens="t=p|tenant|operator|s|c|m",
            case_api_base_url="http://127.0.0.1:9",
            case_api_token="tok",
            evidence_base_url="http://127.0.0.1:9",
            evidence_token="tok",
            default_deadline_seconds=60,
            contract_version="sentinel.task-contracts.v1",
            database_url=f"sqlite:///{tmp_path / 'd.db'}",
        )
    )
    assert app is not None
