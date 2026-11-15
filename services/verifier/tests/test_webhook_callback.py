"""Credit closure must permit case-api to fetch the assessment during a webhook."""

from __future__ import annotations

import asyncio

import httpx
from tests.conftest import CASE_ID, auth_header, signed_webhook

from sentinel_verifier.domain.types import Credit, Refund


def test_credit_webhook_allows_case_api_assessment_callback(
    memory_client, webhook_body, tokens, verification_request, monkeypatch
):
    bind = memory_client.post(
        "/v1/rechecks",
        json=verification_request,
        headers={**auth_header(tokens["workflow"]), "Idempotency-Key": "callback-bind"},
    )
    assert bind.status_code == 202

    memory_client.provider.seed_refund(
        Refund(
            action_id=verification_request["action_id"],
            provider_ref=verification_request["provider_ref"],
            transaction_ref="TXN-B",
            amount_minor=150000,
            currency="INR",
            status="PROVIDER_CONFIRMED",
        )
    )
    memory_client.provider.seed_credit(
        Credit(
            provider_ref=verification_request["provider_ref"],
            confirmed=True,
            observed_at="2026-11-13T12:00:00Z",
        )
    )
    submit_result = memory_client.case_api.submit_result

    async def scenario():
        loop = asyncio.get_running_loop()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=memory_client.app), base_url="http://verifier"
        ) as client:

            async def fetch_assessment(assessment_id):
                response = await client.get(
                    f"/v1/assessments/{assessment_id}", headers=auth_header(tokens["workflow"])
                )
                assert response.status_code == 200
                assert response.json()["status"] == "VERIFIED"

            def validate_then_submit(case_id, result):
                # Real case-api synchronously calls back before accepting verified closure.
                callback = asyncio.run_coroutine_threadsafe(
                    fetch_assessment(result["assessment_id"]), loop
                )
                callback.result(timeout=2)
                return submit_result(case_id, result)

            monkeypatch.setattr(memory_client.case_api, "submit_result", validate_then_submit)
            raw, signature = signed_webhook({**webhook_body, "type": "CREDIT_STATUS"})
            response = await client.post(
                "/v1/webhooks/simulator",
                content=raw,
                headers={"X-Sentinel-Signature": signature, "Content-Type": "application/json"},
            )
            assert response.status_code == 202
            assert memory_client.case_api.cases[CASE_ID]["status"] == "VERIFIED_RESOLVED"

    asyncio.run(scenario())
