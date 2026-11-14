"""Unit-level HttpPeerBundle drivers against httpx mocks (no live stack)."""

from __future__ import annotations

import json

import httpx

from sentinel_core_assembly.adapters.reference import HttpPeerBundle, PeerFault
from sentinel_core_assembly.adapters.sandbox_matrix import default_tokens, journey_seed
from sentinel_core_assembly.application.assembly import run_assembly
from sentinel_core_assembly.domain.types import (
    CONTRACT_VERSION,
    REQUIRED_PEERS,
    ArtifactRef,
    RunInput,
)

TOKENS = default_tokens()
BASES = {port: f"http://peer.test/{port}" for port in REQUIRED_PEERS}


def _bundle(handler) -> HttpPeerBundle:
    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    return HttpPeerBundle(endpoints=BASES, client=client, tokens=TOKENS)


def test_capabilities_require_real_peers_mode_in_assembly() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url).endswith("/v1/capabilities"):
            # Return fixture mode for payment-provider → assembly FAIL
            body = {
                "contract_version": CONTRACT_VERSION,
                "component": "mock",
                "mode": "fixture" if "payment-provider" in str(request.url) else "real-peers",
            }
            return httpx.Response(200, json=body)
        return httpx.Response(404)

    peers = _bundle(handler)
    report = run_assembly(
        RunInput(
            contract_version=CONTRACT_VERSION,
            run_id="probe-mode",
            mode="real-peers",
            input_artifacts=(
                ArtifactRef(
                    kind="bundle",
                    uri="memory://bundle",
                    sha256="e" * 64,
                    component_version="0.1.0",
                    evidence_mode="real-component",
                ),
            ),
        ),
        peers,
    )
    assert report.status == "FAIL"
    assert report.payment_provider == "simulator"
    assert "PEER_FIXTURE_NOT_REAL" in {c.reason_code for c in report.checks}


def test_run_pending_http_driver() -> None:
    seed = journey_seed("pending")

    def handler(request: httpx.Request) -> httpx.Response:
        if "/v1/transactions" in str(request.url):
            assert seed["order_reference"] in str(request.url)
            return httpx.Response(
                200,
                json={
                    "payments": [
                        {
                            "transaction_ref": "TXN-P",
                            "order_reference": seed["order_reference"],
                            "status": "PENDING",
                            "amount_minor": 150000,
                            "currency": "INR",
                        }
                    ]
                },
            )
        return httpx.Response(404)

    outcome = _bundle(handler).run_pending()
    assert outcome["terminal_state"] == "WAITING_ON_EVIDENCE"
    assert outcome["payment_status"] == "PENDING"
    assert outcome["refunded_minor"] == 0


def test_run_merchant_mismatch_http_driver() -> None:
    seed = journey_seed("merchant_mismatch")

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if f"/v1/orders/{seed['order_reference']}" in url:
            return httpx.Response(
                200,
                json={
                    "order_reference": seed["order_reference"],
                    "paid": False,
                    "fulfilled_order_count": 0,
                    "merchant_confirmed_duplicate": False,
                },
            )
        if "/v1/transactions" in url:
            return httpx.Response(
                200,
                json={
                    "payments": [
                        {
                            "transaction_ref": "TXN-M",
                            "status": "CAPTURED",
                            "amount_minor": 150000,
                            "currency": "INR",
                        }
                    ]
                },
            )
        return httpx.Response(404)

    outcome = _bundle(handler).run_merchant_mismatch()
    assert outcome["terminal_state"] == "NEEDS_HUMAN"
    assert outcome["approval_required"] is True
    assert outcome["order_paid"] is False


def test_run_duplicate_payment_http_driver() -> None:
    seed = journey_seed("duplicate_payment")
    provider_ref = seed["provider_ref"]
    state = {"refunds": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        method = request.method
        if method == "POST" and url.endswith("/v1/admin/faults/reset"):
            return httpx.Response(200, json={"outage": False, "timeout_after_accept": False})
        if method == "PUT" and url.endswith("/v1/admin/faults"):
            return httpx.Response(200, json={"timeout_after_accept": True})
        if method == "POST" and url.endswith("/v1/refunds"):
            state["refunds"] += 1
            return httpx.Response(504, json={"code": "TIMEOUT_AFTER_ACCEPT", "message": "timeout"})
        if method == "GET" and f"/v1/refunds/{provider_ref}" in url:
            return httpx.Response(
                200,
                json={
                    "provider_ref": provider_ref,
                    "status": "PENDING",
                    "amount_minor": 150000,
                },
            )
        if method == "GET" and f"/v1/admin/refunds/{provider_ref}/stats" in url:
            return httpx.Response(
                200,
                json={
                    "provider_ref": provider_ref,
                    "accept_count": state["refunds"],
                    "side_effect_count": 1,
                    "timeout_count": state["refunds"],
                },
            )
        if method == "POST" and f"/v1/admin/refunds/{provider_ref}/confirm" in url:
            return httpx.Response(200, json={"status": "PROVIDER_CONFIRMED"})
        if method == "POST" and f"/v1/admin/credits/{provider_ref}/confirm" in url:
            return httpx.Response(
                200,
                json={"provider_ref": provider_ref, "confirmed": True},
            )
        if method == "GET" and f"/v1/credits/{provider_ref}" in url:
            return httpx.Response(
                200,
                json={"provider_ref": provider_ref, "confirmed": True},
            )
        return httpx.Response(404, json={"code": "NOT_FOUND"})

    outcome = _bundle(handler).run_duplicate_payment()
    assert outcome["terminal_state"] == "VERIFIED_RESOLVED"
    assert outcome["amount_minor"] == 150000
    assert outcome["refunded_minor"] == 150000
    assert outcome["refund_side_effect_count"] == 1
    assert outcome["timeout_recovered"] is True
    assert outcome["credit_confirmed"] is True
    assert outcome["approval_required"] is True


def test_run_refund_pending_not_credit() -> None:
    seed = journey_seed("refund_pending")
    provider_ref = seed["provider_ref"]

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        method = request.method
        if method == "GET" and f"/v1/refunds/{provider_ref}" in url:
            return httpx.Response(
                200,
                json={"provider_ref": provider_ref, "status": "PENDING", "amount_minor": 150000},
            )
        if method == "GET" and f"/v1/credits/{provider_ref}" in url:
            return httpx.Response(404, json={"code": "NOT_FOUND"})
        return httpx.Response(404)

    outcome = _bundle(handler).run_refund_pending()
    assert outcome["terminal_state"] == "WAITING_ON_PROVIDER"
    assert outcome["refund_status"] == "PENDING"
    assert outcome["credit_confirmed"] is False
    assert outcome["refunded_minor"] == 0
    assert outcome["path"] == "provider-sandbox-only"


def test_timeout_recovered_tracks_504_status() -> None:
    """Happy path: first refund 504 → timeout_recovered True (status tracking)."""
    seed = journey_seed("duplicate_payment")
    provider_ref = seed["provider_ref"]
    state = {"refunds": 0, "resets": 0, "confirms": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        method = request.method
        if method == "POST" and url.endswith("/v1/admin/faults/reset"):
            state["resets"] += 1
            return httpx.Response(200, json={"outage": False, "timeout_after_accept": False})
        if method == "PUT" and url.endswith("/v1/admin/faults"):
            return httpx.Response(200, json={"timeout_after_accept": True})
        if method == "POST" and url.endswith("/v1/refunds"):
            state["refunds"] += 1
            return httpx.Response(504, json={"code": "TIMEOUT_AFTER_ACCEPT", "message": "timeout"})
        if method == "GET" and f"/v1/refunds/{provider_ref}" in url:
            return httpx.Response(
                200,
                json={
                    "provider_ref": provider_ref,
                    "status": "PENDING",
                    "amount_minor": 150000,
                },
            )
        if method == "GET" and f"/v1/admin/refunds/{provider_ref}/stats" in url:
            return httpx.Response(
                200,
                json={
                    "provider_ref": provider_ref,
                    "accept_count": state["refunds"],
                    "side_effect_count": 1,
                    "timeout_count": state["refunds"],
                },
            )
        if method == "POST" and f"/v1/admin/refunds/{provider_ref}/confirm" in url:
            state["confirms"] += 1
            return httpx.Response(200, json={"status": "PROVIDER_CONFIRMED"})
        if method == "POST" and f"/v1/admin/credits/{provider_ref}/confirm" in url:
            state["confirms"] += 1
            return httpx.Response(200, json={"provider_ref": provider_ref, "confirmed": True})
        if method == "GET" and f"/v1/credits/{provider_ref}" in url:
            return httpx.Response(200, json={"provider_ref": provider_ref, "confirmed": True})
        return httpx.Response(404, json={"code": "NOT_FOUND"})

    outcome = _bundle(handler).run_duplicate_payment()
    assert outcome["timeout_recovered"] is True
    assert state["confirms"] == 2
    assert state["resets"] >= 2  # initial + finally


def test_non_504_aborts_without_credit_confirm() -> None:
    """After timeout arm, 202 must PeerFault; faults/reset still runs; no confirm."""
    seed = journey_seed("duplicate_payment")
    provider_ref = seed["provider_ref"]
    state = {"resets": 0, "confirms": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        method = request.method
        if method == "POST" and url.endswith("/v1/admin/faults/reset"):
            state["resets"] += 1
            return httpx.Response(200, json={})
        if method == "PUT" and url.endswith("/v1/admin/faults"):
            return httpx.Response(200, json={"timeout_after_accept": True})
        if method == "POST" and url.endswith("/v1/refunds"):
            return httpx.Response(
                202,
                json={"provider_ref": provider_ref, "status": "PENDING", "amount_minor": 150000},
            )
        if method == "POST" and "/v1/admin/refunds/" in url and url.endswith("/confirm"):
            state["confirms"] += 1
            return httpx.Response(200, json={"status": "PROVIDER_CONFIRMED"})
        if method == "POST" and "/v1/admin/credits/" in url and url.endswith("/confirm"):
            state["confirms"] += 1
            return httpx.Response(200, json={"provider_ref": provider_ref, "confirmed": True})
        return httpx.Response(404)

    try:
        _bundle(handler).run_duplicate_payment()
        raise AssertionError("expected PeerFault")
    except PeerFault as exc:
        assert exc.code == "JOURNEY_PROVIDER"
    assert state["confirms"] == 0
    assert state["resets"] >= 2  # initial + finally


def test_require_full_path_fails_closed(monkeypatch) -> None:
    monkeypatch.setenv("SENTINEL_V1_REQUIRE_FULL_PATH", "1")
    monkeypatch.delenv("SENTINEL_V1_AUTHORITY_PATH", raising=False)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/v1/capabilities"):
            return httpx.Response(
                200,
                json={
                    "contract_version": CONTRACT_VERSION,
                    "component": "mock",
                    "mode": "real-peers",
                },
            )
        # Provider journeys fail; without AUTHORITY_PATH, path stays provider-only.
        return httpx.Response(500)

    report = run_assembly(
        RunInput(
            contract_version=CONTRACT_VERSION,
            run_id="full-path-gate",
            mode="real-peers",
            input_artifacts=(
                ArtifactRef(
                    kind="bundle",
                    uri="memory://bundle",
                    sha256="a" * 64,
                    component_version="0.1.0",
                    evidence_mode="real-component",
                ),
            ),
            parameters={"journeys": "pending"},
        ),
        _bundle(handler),
    )
    assert report.status == "FAIL"
    assert report.path == "provider-sandbox-only"
    assert report.sn009_authority_exercised is False
    assert "FULL_PATH_REQUIRED_BUT_PROVIDER_SANDBOX_ONLY" in {c.reason_code for c in report.checks}


def test_authority_path_http_gated_without_env(monkeypatch) -> None:
    monkeypatch.delenv("SENTINEL_V1_AUTHORITY_PATH", raising=False)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    try:
        _bundle(handler).run_browser_to_credit()
        raise AssertionError("expected PeerFault")
    except PeerFault as exc:
        assert exc.code == "AUTHORITY_PATH_GATED"


def test_browser_to_credit_http_sets_sn009(monkeypatch) -> None:
    monkeypatch.setenv("SENTINEL_V1_AUTHORITY_PATH", "1")
    seed = journey_seed("browser_to_credit")
    provider_ref = "refund-authority-live"
    action_id = "action-authority-live"
    approval_id = "approval-authority-live"

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        method = request.method
        if method == "POST" and url.endswith("/v1/cases"):
            return httpx.Response(
                202,
                json={
                    "case_id": seed["case_id"],
                    "status": "RECEIVED",
                    "status_url": "/v1/cases/x",
                },
            )
        if method == "POST" and url.endswith("/v1/runs"):
            return httpx.Response(
                202, json={"contract_version": CONTRACT_VERSION, "job_id": "j1", "accepted": True}
            )
        if method == "POST" and url.endswith("/v1/actions/proposals"):
            return httpx.Response(
                201,
                json={
                    "action_id": action_id,
                    "provider_ref": None,
                    "status": "PROPOSED",
                    "action_digest": seed["action_digest"],
                    "payload": {},
                },
            )
        if method == "POST" and f"/v1/actions/{action_id}/decisions" in url:
            return httpx.Response(
                200,
                json={
                    "approval_id": approval_id,
                    "decision": "APPROVE",
                    "action_digest": seed["action_digest"],
                    "case_revision": seed["case_revision"],
                    "policy_version": seed["policy_version"],
                    "expires_at": seed["expires_at"],
                    "reviewer_id": "supervisor-demo",
                },
            )
        if method == "POST" and url.endswith("/v1/actions/reservations"):
            return httpx.Response(
                201,
                json={
                    "action_id": action_id,
                    "provider_ref": provider_ref,
                    "status": "RESERVED",
                    "action_digest": seed["action_digest"],
                    "payload": {},
                },
            )
        if method == "POST" and url.endswith("/v1/actions/claims"):
            return httpx.Response(
                200,
                json={
                    "commands": [
                        {
                            "action_id": action_id,
                            "provider_ref": provider_ref,
                            "payload": {},
                            "action_digest": seed["action_digest"],
                            "lease_id": "lease-1",
                            "lease_expires_at": "2099-01-01T00:00:00Z",
                            "provider_capabilities": {},
                        }
                    ]
                },
            )
        if method == "POST" and url.endswith("/v1/refunds"):
            return httpx.Response(202, json={"provider_ref": provider_ref, "status": "PENDING"})
        if method == "POST" and f"/v1/actions/{action_id}/outcomes" in url:
            return httpx.Response(
                200,
                json={
                    "action_id": action_id,
                    "provider_ref": provider_ref,
                    "status": "PROVIDER_CONFIRMED",
                    "action_digest": seed["action_digest"],
                    "payload": {},
                },
            )
        if method == "POST" and url.endswith("/v1/assessments"):
            return httpx.Response(200, json={"assessment_id": "assess-1"})
        if method == "GET" and f"/v1/credits/{provider_ref}" in url:
            return httpx.Response(200, json={"provider_ref": provider_ref, "confirmed": True})
        if method == "POST" and "/v1/internal/cases/" in url and url.endswith("/results"):
            return httpx.Response(200, json={"status": "VERIFIED_RESOLVED", "revision": 3})
        if method == "GET" and f"/v1/admin/refunds/{provider_ref}/stats" in url:
            return httpx.Response(200, json={"side_effect_count": 1})
        return httpx.Response(404, json={"code": "NOT_FOUND"})

    outcome = _bundle(handler).run_browser_to_credit()
    assert outcome["sn009_authority_exercised"] is True
    assert outcome["path"] == "browser-to-credit"
    assert outcome["customer_closed"] is True
    assert outcome["credit_confirmed"] is True
    assert "dispatcher" in outcome["stages"]


def test_duplicate_approval_deny_http(monkeypatch) -> None:
    monkeypatch.setenv("SENTINEL_V1_AUTHORITY_PATH", "1")
    seed = journey_seed("duplicate_approval_deny")
    action_id = "action-dup-deny"
    decisions = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        method = request.method
        if method == "POST" and url.endswith("/v1/actions/proposals"):
            return httpx.Response(
                201,
                json={
                    "action_id": action_id,
                    "status": "PROPOSED",
                    "action_digest": seed["action_digest"],
                    "payload": {},
                    "provider_ref": None,
                },
            )
        if method == "POST" and f"/v1/actions/{action_id}/decisions" in url:
            decisions["n"] += 1
            if decisions["n"] == 1:
                return httpx.Response(
                    200,
                    json={
                        "approval_id": "approval-1",
                        "decision": "APPROVE",
                        "action_digest": seed["action_digest"],
                        "case_revision": 1,
                        "policy_version": seed["policy_version"],
                        "expires_at": seed["expires_at"],
                        "reviewer_id": "supervisor-demo",
                    },
                )
            return httpx.Response(409, json={"code": "CONFLICT", "message": "already decided"})
        return httpx.Response(404)

    outcome = _bundle(handler).run_duplicate_approval_deny()
    assert outcome["duplicate_approval_denied"] is True
    assert outcome["sn009_authority_exercised"] is True
    assert outcome["path"] == "browser-to-credit"
    assert outcome["refund_side_effect_count"] == 0


def test_real_peers_authority_assembly_labels(monkeypatch) -> None:
    monkeypatch.setenv("SENTINEL_V1_AUTHORITY_PATH", "1")
    seed = journey_seed("browser_to_credit")
    deny_seed = journey_seed("duplicate_approval_deny")
    state = {"proposals": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        method = request.method
        if request.url.path.endswith("/v1/capabilities"):
            return httpx.Response(
                200,
                json={
                    "contract_version": CONTRACT_VERSION,
                    "component": "mock",
                    "mode": "real-peers",
                },
            )
        if method == "POST" and url.endswith("/v1/cases"):
            return httpx.Response(
                202, json={"case_id": seed["case_id"], "status": "RECEIVED", "status_url": "/x"}
            )
        if method == "POST" and url.endswith("/v1/runs"):
            return httpx.Response(
                202, json={"contract_version": CONTRACT_VERSION, "job_id": "j1", "accepted": True}
            )
        if method == "POST" and url.endswith("/v1/actions/proposals"):
            state["proposals"] += 1
            aid = f"action-{state['proposals']}"
            return httpx.Response(
                201,
                json={
                    "action_id": aid,
                    "status": "PROPOSED",
                    "action_digest": seed["action_digest"],
                    "payload": {},
                    "provider_ref": None,
                },
            )
        if "/decisions" in url and method == "POST":
            body = json.loads(request.content.decode()) if request.content else {}
            if body.get("decision") == "REJECT":
                return httpx.Response(409, json={"code": "CONFLICT"})
            return httpx.Response(
                200,
                json={
                    "approval_id": "approval-x",
                    "decision": "APPROVE",
                    "action_digest": body.get("action_digest", seed["action_digest"]),
                    "case_revision": 1,
                    "policy_version": seed["policy_version"],
                    "expires_at": seed["expires_at"],
                    "reviewer_id": "supervisor-demo",
                },
            )
        if method == "POST" and url.endswith("/v1/actions/reservations"):
            return httpx.Response(
                201,
                json={
                    "action_id": "action-1",
                    "provider_ref": "refund-authority-live",
                    "status": "RESERVED",
                    "action_digest": seed["action_digest"],
                    "payload": {},
                },
            )
        if method == "POST" and url.endswith("/v1/actions/claims"):
            return httpx.Response(
                200,
                json={
                    "commands": [
                        {
                            "action_id": "action-1",
                            "provider_ref": "refund-authority-live",
                            "payload": {},
                            "action_digest": seed["action_digest"],
                            "lease_id": "lease-1",
                            "lease_expires_at": "2099-01-01T00:00:00Z",
                            "provider_capabilities": {},
                        }
                    ]
                },
            )
        if method == "POST" and url.endswith("/v1/refunds"):
            return httpx.Response(
                202, json={"provider_ref": "refund-authority-live", "status": "PENDING"}
            )
        if "/outcomes" in url and method == "POST":
            return httpx.Response(
                200,
                json={
                    "action_id": "action-1",
                    "provider_ref": "refund-authority-live",
                    "status": "PROVIDER_CONFIRMED",
                    "action_digest": seed["action_digest"],
                    "payload": {},
                },
            )
        if method == "POST" and url.endswith("/v1/assessments"):
            return httpx.Response(200, json={"assessment_id": "assess-1"})
        if "/credits/" in url and method == "GET":
            return httpx.Response(
                200, json={"provider_ref": "refund-authority-live", "confirmed": True}
            )
        if "/results" in url and method == "POST":
            return httpx.Response(200, json={"status": "VERIFIED_RESOLVED", "revision": 3})
        if "/stats" in url:
            return httpx.Response(200, json={"side_effect_count": 1})
        return httpx.Response(404)

    assert deny_seed["operation_key"]
    report = run_assembly(
        RunInput(
            contract_version=CONTRACT_VERSION,
            run_id="authority-labels",
            mode="real-peers",
            input_artifacts=(
                ArtifactRef(
                    kind="bundle",
                    uri="memory://bundle",
                    sha256="b" * 64,
                    component_version="0.1.0",
                    evidence_mode="real-component",
                ),
            ),
            parameters={"journeys": "browser_to_credit,duplicate_approval_deny"},
        ),
        _bundle(handler),
    )
    assert report.status == "PASS", report.as_dict()
    assert report.path == "browser-to-credit"
    assert report.sn009_authority_exercised is True
    assert report.assembled_mvp_claimed is False
    assert report.payment_provider == "simulator"


def test_missing_seed_fails_closed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"code": "NOT_FOUND"})

    try:
        _bundle(handler).run_pending()
        raise AssertionError("expected PeerFault")
    except PeerFault as exc:
        assert exc.code == "JOURNEY_SEED_MISSING"


def test_real_peers_report_labels_simulator_provider() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/v1/capabilities"):
            return httpx.Response(
                200,
                json={
                    "contract_version": CONTRACT_VERSION,
                    "component": "mock",
                    "mode": "real-peers",
                },
            )
        # Journeys will fail without full mocks; only need probe path for label check.
        calls["n"] += 1
        return httpx.Response(500)

    # Probe OK; journey HTTP fails — report still labels payment_provider=simulator.
    peers = _bundle(handler)
    report = run_assembly(
        RunInput(
            contract_version=CONTRACT_VERSION,
            run_id="label-sim",
            mode="real-peers",
            input_artifacts=(
                ArtifactRef(
                    kind="bundle",
                    uri="memory://bundle",
                    sha256="f" * 64,
                    component_version="0.1.0",
                    evidence_mode="real-component",
                ),
            ),
            parameters={"journeys": "pending"},
        ),
        peers,
    )
    assert report.payment_provider == "simulator"
    assert report.path == "provider-sandbox-only"
    assert report.sn009_authority_exercised is False
    assert report.as_dict()["payment_provider"] == "simulator"
    assert report.as_dict()["path"] == "provider-sandbox-only"
