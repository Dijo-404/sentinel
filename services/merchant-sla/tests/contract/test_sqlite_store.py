"""Durable sqlite SLA store for real-peers."""

from __future__ import annotations

from pathlib import Path

from sentinel_merchant_sla.adapters.sqlite_store import SqliteSlaStore
from sentinel_merchant_sla.bootstrap import Settings, build_app
from sentinel_merchant_sla.contracts import SlaPolicy

PRINCIPALS = Path(__file__).resolve().parents[2] / "contracts" / "principals.json"


def test_sqlite_sla_round_trip(tmp_path: Path):
    store = SqliteSlaStore(tmp_path / "sla.db")
    policy = SlaPolicy(
        policy_id="pol-1",
        tenant_id="tenant-demo",
        merchant_ref="merchant-demo",
        respond_within_seconds=3600,
        resolve_within_seconds=86400,
    )
    store.put_policy(policy)
    task_id = store.next_id("task")
    reopened = SqliteSlaStore(tmp_path / "sla.db")
    assert reopened.get_policy("pol-1") is not None
    assert task_id == "task-1"
    assert reopened.next_id("task") == "task-2"


def test_real_peers_accepts_database_url(tmp_path: Path):
    app = build_app(
        settings=Settings(
            mode="real-peers",
            principals_path=PRINCIPALS,
            case_api_base_url="http://127.0.0.1:9",
            case_api_token="tok",
            database_url=f"sqlite:///{tmp_path / 'sla.db'}",
        )
    )
    assert app is not None
