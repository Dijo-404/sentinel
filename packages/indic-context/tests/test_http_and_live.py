from __future__ import annotations

import json
import os

import httpx
import pytest
from fastapi.testclient import TestClient

from sentinel_indic_context.adapters.live_sarvam import LiveSarvamAdapter
from sentinel_indic_context.adapters.settings import Settings
from sentinel_indic_context.application.errors import ConfigurationError, ProviderUnavailableError
from sentinel_indic_context.application.service import IndicContextService
from sentinel_indic_context.bootstrap import build_service
from tests.conftest import load_fixture


def test_http_proposals_fake_mode(app) -> None:
    client = TestClient(app)
    request, _ = load_fixture("tamil_duplicate.json")
    response = client.post(
        "/v1/proposals",
        json=request.model_dump(exclude_none=True),
        headers={"Authorization": "Bearer workflow-token"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "PROPOSAL"
    assert body["original_text"] == request.input.original_text
    assert body["language"] == "ta-IN"
    assert body["inference_report"]["evidence_mode"] == "fake-inference"
    assert body["inference_report"]["native_review_limit"] == "human-review-required-for-refunds"


def test_http_rejects_missing_auth(app) -> None:
    client = TestClient(app)
    request, _ = load_fixture("english_refund.json")
    response = client.post("/v1/proposals", json=request.model_dump(exclude_none=True))
    assert response.status_code == 401


def test_live_mode_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INDIC_CONTEXT_MODE", "live")
    monkeypatch.setenv("INDIC_CONTEXT_SARVAM_API_KEY", "")
    with pytest.raises(ConfigurationError):
        build_service(Settings())


def test_live_adapter_reports_provider_observation() -> None:
    request, principal = load_fixture("english_refund.json")

    def handler(http_request: httpx.Request) -> httpx.Response:
        assert http_request.url.path.endswith("/v1/chat/completions")
        payload = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "outcome": "PROPOSAL",
                                "proposal": {
                                    "action": "REQUEST_REFUND",
                                    "case_id": "case-demo-42",
                                    "case_revision": 2,
                                    "transaction_ref": "TXN-B",
                                    "amount_minor": 150000,
                                    "currency": "INR",
                                    "destination": "ORIGINAL_PAYMENT_ROUTE",
                                    "evidence_ids": ["evidence-payment-b", "evidence-order"],
                                    "policy_version": "demo-policy-v1",
                                },
                                "reason_codes": ["DUPLICATE_PAYMENT"],
                            },
                            ensure_ascii=False,
                        )
                    }
                }
            ],
            "usage": {"prompt_tokens": 12, "completion_tokens": 34},
        }
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)
    adapter = LiveSarvamAdapter(
        api_key="test-key",
        base_url="https://api.sarvam.ai",
        model_id="sarvam-m",
        transport=transport,
    )
    service = IndicContextService(adapter, native_review_limit="human-review-required-for-refunds")
    result, report, _ = service.propose(request, principal)
    assert result.outcome == "PROPOSAL"
    assert report.evidence_mode == "provider-observation"
    assert report.model_id == "sarvam-m"
    assert report.cost_units == 46.0
    assert report.latency_ms >= 0
    assert result.original_text == request.input.original_text


def test_live_adapter_no_fixture_fallback_on_outage() -> None:
    request, _ = load_fixture("english_refund.json")

    def handler(_http_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    adapter = LiveSarvamAdapter(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ProviderUnavailableError):
        adapter.propose(request)


@pytest.mark.live
def test_opt_in_live_call_skipped_by_default() -> None:
    if os.environ.get("INDIC_CONTEXT_LIVE") != "1":
        pytest.skip("live Sarvam call opt-in only")
    settings = Settings()
    assert settings.mode == "live"
    service = build_service(settings)
    request, principal = load_fixture("english_refund.json")
    _result, report, _ = service.propose(request, principal)
    assert report.evidence_mode == "provider-observation"


def test_capabilities_and_readyz(app) -> None:
    client = TestClient(app)
    assert client.get("/healthz").json()["status"] == "ok"
    caps = client.get("/v1/capabilities").json()
    assert caps["port"] == "indic-context.v1"
    assert caps["mode"] == "fake"
