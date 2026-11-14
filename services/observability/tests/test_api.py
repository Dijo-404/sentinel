"""HTTP: health, capabilities, ingest, signals/spans list, auth."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from tests.conftest import auth, sample_signal


def test_health_ready_capabilities(client: TestClient):
    assert client.get("/healthz").json() == {"status": "ok"}
    ready = client.get("/readyz").json()
    assert ready["status"] == "ready"
    assert ready["mode"] == "fixture"
    caps = client.get("/v1/capabilities").json()
    assert caps["contract_version"] == "sentinel.task-contracts.v1"
    assert caps["component"] == "observability"
    assert caps["mode"] == "fixture"
    assert caps["port"] == "observability.v1"
    assert caps["financial_audit"] is False
    assert caps["financial_authority"] is False


def test_signals_empty(client: TestClient):
    response = client.get("/v1/signals", headers=auth())
    assert response.status_code == 200
    body = response.json()
    assert body["signals"] == []
    assert body["financial_audit"] is False


def test_spans_empty(client: TestClient):
    response = client.get("/v1/spans", headers=auth())
    assert response.status_code == 200
    body = response.json()
    assert body["spans"] == []
    assert body["financial_audit"] is False


def test_ingest_then_list_signals_and_spans(client: TestClient):
    payload = {
        "signals": [
            {
                "signal_id": "sig-ingest-1",
                "kind": "span",
                "name": "approval.decide",
                "attributes": {"approval_id": "apr-1"},
                "events": [],
                "recorded_at": "2026-11-14T13:00:00Z",
            }
        ]
    }
    ingest = client.post("/v1/ingest", headers=auth(), json=payload)
    assert ingest.status_code == 200
    assert ingest.json() == {"accepted": 1, "financial_audit": False}

    signals = client.get("/v1/signals", headers=auth()).json()
    assert len(signals["signals"]) == 1
    item = signals["signals"][0]
    assert item["signal_id"] == "sig-ingest-1"
    assert item["kind"] == "span"
    assert item["name"] == "approval.decide"
    assert item["attributes"] == {"approval_id": "apr-1"}
    assert item["events"] == []
    assert item["recorded_at"] == "2026-11-14T13:00:00Z"
    assert signals["financial_audit"] is False

    spans = client.get("/v1/spans", headers=auth()).json()
    assert spans["financial_audit"] is False
    assert spans["spans"] == [
        {
            "name": "approval.decide",
            "attributes": {"approval_id": "apr-1"},
            "events": [],
        }
    ]


def test_ingest_accepts_telemetry_spans_shape(client: TestClient):
    """Align with packages/telemetry RecordedSpan wire fields."""
    payload = {
        "spans": [
            {
                "name": "worker.execute",
                "attributes": {"worker_id": "w-1"},
                "events": [{"name": "retry", "attributes": {"event.kind": "retry"}}],
            }
        ]
    }
    ingest = client.post("/v1/ingest", headers=auth(), json=payload)
    assert ingest.status_code == 200
    assert ingest.json()["accepted"] == 1
    spans = client.get("/v1/spans", headers=auth()).json()["spans"]
    assert spans[0]["name"] == "worker.execute"
    assert spans[0]["attributes"] == {"worker_id": "w-1"}
    assert spans[0]["events"] == [{"name": "retry", "attributes": {"event.kind": "retry"}}]


def test_signals_newest_first_and_cap_50(client: TestClient, store):
    base = datetime(2026, 11, 14, 12, 0, tzinfo=UTC)
    for i in range(55):
        store.put(
            sample_signal(
                signal_id=f"sig-{i:03d}",
                recorded_at=(base + timedelta(seconds=i)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                name=f"span.{i}",
            )
        )
    response = client.get("/v1/signals", headers=auth())
    assert response.status_code == 200
    items = response.json()["signals"]
    assert len(items) == 50
    recorded = [row["recorded_at"] for row in items]
    assert recorded == sorted(recorded, reverse=True)
    assert items[0]["signal_id"] == "sig-054"


def test_signals_tenant_scoped(client: TestClient, store):
    store.put(sample_signal(signal_id="sig-demo"))
    store.put(
        sample_signal(
            signal_id="sig-other",
            tenant_id="tenant-other",
            name="other.span",
        )
    )
    demo = client.get("/v1/signals", headers=auth("admin-token"))
    assert [i["signal_id"] for i in demo.json()["signals"]] == ["sig-demo"]
    other = client.get("/v1/signals", headers=auth("other-tenant-token"))
    assert [i["signal_id"] for i in other.json()["signals"]] == ["sig-other"]


def test_signals_requires_bearer(client: TestClient):
    response = client.get("/v1/signals")
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_ingest_requires_bearer(client: TestClient):
    response = client.post("/v1/ingest", json={"signals": []})
    assert response.status_code == 403


def test_operator_denied(client: TestClient, store):
    store.put(sample_signal())
    assert client.get("/v1/signals", headers=auth("operator-token")).status_code == 403
    assert client.get("/v1/spans", headers=auth("operator-token")).status_code == 403
    assert (
        client.post(
            "/v1/ingest",
            headers=auth("operator-token"),
            json={"signals": []},
        ).status_code
        == 403
    )


def test_sandbox_admin_allowed(client: TestClient):
    response = client.get("/v1/signals", headers=auth("sandbox-admin-token"))
    assert response.status_code == 200


def test_signal_wire_shape_never_claims_financial_audit(client: TestClient, store):
    store.put(sample_signal())
    body = client.get("/v1/signals", headers=auth()).json()
    item = body["signals"][0]
    assert item == {
        "signal_id": "sig-1",
        "kind": "span",
        "name": "request.handle",
        "attributes": {"request_id": "req-demo-1", "case_id": "case-demo-42"},
        "events": [{"name": "accepted", "attributes": {"event.kind": "accepted"}}],
        "recorded_at": "2026-11-14T12:00:00Z",
    }
    assert "financial_audit" not in item
    assert body["financial_audit"] is False
    assert "amount" not in item
    assert "ledger" not in item
