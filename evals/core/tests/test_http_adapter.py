from __future__ import annotations

import json
from typing import Any

from sentinel_evaluation.adapters.http_candidate import HttpCandidateAdapter
from sentinel_evaluation.domain.models import EvalFixture, ExpectedOutcome


class _FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._raw = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._raw

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def test_http_candidate_adapter_posts_and_parses() -> None:
    fixture = EvalFixture(
        fixture_id="http-1",
        suite="core",
        version="eval-fixtures-v1",
        split="development",
        seed=1,
        tenant_id="demo-tenant-a",
        eligible_refund_minor=10,
        currency="INR",
        credit_actually_confirmed=False,
        allowed_actions=("STATUS_UPDATE",),
        expected=ExpectedOutcome(
            terminal_state="WAITING_EXTERNAL",
            refund_side_effect_count=0,
            refunded_minor=0,
            approval_required=False,
        ),
    )
    captured: dict[str, Any] = {}

    def opener(request: Any, timeout: float = 0) -> _FakeResponse:
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return _FakeResponse(
            {
                "terminal_state": "WAITING_EXTERNAL",
                "refund_side_effect_count": 0,
                "refunded_minor": 0,
                "currency": "INR",
                "actions": ["STATUS_UPDATE"],
                "accessed_tenant_id": "demo-tenant-a",
                "claims_credit_confirmed": False,
                "approval_obtained": True,
                "model_mode": "fake",
            }
        )

    adapter = HttpCandidateAdapter("http://127.0.0.1:9/candidate", opener=opener)
    obs = adapter.run(fixture)
    assert captured["url"] == "http://127.0.0.1:9/candidate"
    assert captured["body"]["fixture_id"] == "http-1"
    assert obs.terminal_state == "WAITING_EXTERNAL"
    assert obs.actions == ("STATUS_UPDATE",)
