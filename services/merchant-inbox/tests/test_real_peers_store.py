"""Real-peers refuses fixture records; sqlite store is allowed."""

from __future__ import annotations

from pathlib import Path

import pytest

from sentinel_merchant_inbox.adapters.sqlite_store import SqliteInboxStore
from sentinel_merchant_inbox.bootstrap import build_app
from sentinel_merchant_inbox.contracts import ExceptionItem
from sentinel_merchant_inbox.domain.errors import PeerUnavailableError


def test_real_peers_refuses_fixture_records(monkeypatch):
    monkeypatch.setenv("MERCHANT_INBOX_PEER_TOKEN", "non-demo-peer-token")
    monkeypatch.setenv("CASE_API_BASE_URL", "http://127.0.0.1:9")
    monkeypatch.setenv("EVIDENCE_BASE_URL", "http://127.0.0.1:9")
    monkeypatch.delenv("MERCHANT_INBOX_DATABASE_URL", raising=False)
    with pytest.raises(PeerUnavailableError, match="refuses fixture records"):
        build_app(mode="real-peers")


def test_sqlite_inbox_round_trip(tmp_path: Path):
    store = SqliteInboxStore(tmp_path / "inbox.db")
    item = ExceptionItem(
        item_id="exc-1",
        tenant_id="tenant-demo",
        merchant_ref="merchant-demo",
        kind="PAID_UNFULFILLED",
        amount_minor=100,
        currency="INR",
        status="OPEN",
        notes=[],
    )
    store.save_item(item)
    reopened = SqliteInboxStore(tmp_path / "inbox.db")
    loaded = reopened.get_item(tenant_id="tenant-demo", item_id="exc-1")
    assert loaded is not None
    assert loaded.amount_minor == 100


def test_real_peers_accepts_database_url(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("MERCHANT_INBOX_PEER_TOKEN", "non-demo-peer-token")
    monkeypatch.setenv("CASE_API_BASE_URL", "http://127.0.0.1:9")
    monkeypatch.setenv("EVIDENCE_BASE_URL", "http://127.0.0.1:9")
    monkeypatch.setenv("MERCHANT_INBOX_DATABASE_URL", f"sqlite:///{tmp_path / 'inbox.db'}")
    app = build_app(mode="real-peers")
    assert app is not None
