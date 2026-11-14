"""Unit-level HttpPeerBundle drivers against httpx mocks (no live stack)."""

from __future__ import annotations

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
        ),
        _bundle(handler),
    )
    assert report.status == "FAIL"
    assert report.path == "provider-sandbox-only"
    assert report.sn009_authority_exercised is False
    assert "FULL_PATH_REQUIRED_BUT_PROVIDER_SANDBOX_ONLY" in {c.reason_code for c in report.checks}


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
