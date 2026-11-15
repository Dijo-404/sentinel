"""Workflow outbox delivery: transient 409/422/429 retried with bounded backoff."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import text

from sentinel_api.adapters.db.repository import SqlCaseRepository
from sentinel_api.adapters.peers.http_clients import HttpWorkflowClient
from sentinel_api.application.service import CaseService
from sentinel_api.bootstrap import SecureIds
from sentinel_api.domain.types import WorkflowRequest


class FakeClock:
    def __init__(self) -> None:
        self.current = datetime(2026, 11, 15, 12, 0, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self.current

    def advance(self, seconds: float) -> None:
        self.current += timedelta(seconds=seconds)


class ScriptedWorkflowPeer:
    """Real HTTP adapter over a mock transport that replays scripted status codes."""

    def __init__(self, statuses: list[int]) -> None:
        self.statuses = list(statuses)
        self.calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            self.calls += 1
            status = self.statuses.pop(0) if self.statuses else 202
            body = {"accepted": True} if status < 300 else {"code": "NOPE"}
            return httpx.Response(status, json=body)

        client = httpx.Client(transport=httpx.MockTransport(handler))
        self.client = HttpWorkflowClient("http://workflow.test", client=client)


def _setup(engine, statuses, **retry):
    repo = SqlCaseRepository(engine)
    peer = ScriptedWorkflowPeer(statuses)
    clock = FakeClock()
    service = CaseService(
        repo=repo,
        clock=clock,
        ids=SecureIds(),
        workflow=peer.client,
        evidence=None,  # type: ignore[arg-type]
        ledger=None,  # type: ignore[arg-type]
        verifier=None,  # type: ignore[arg-type]
        service_authorization="Bearer token-case-api-service",
        **retry,
    )
    repo.enqueue_workflow(
        tenant_id="tenant-demo",
        request=WorkflowRequest(
            case_id="case-r", case_revision=2, job_key="job-r", event="DECISION"
        ),
    )
    return service, peer, clock


def _row(engine):
    with engine.connect() as conn:
        return conn.execute(
            text(
                "SELECT status, detail, attempts, lease_expires_at FROM workflow_outbox"
                " WHERE job_key = 'job-r'"
            )
        ).one()


def test_transient_422_retried_after_backoff_then_delivered(engine):
    service, peer, clock = _setup(engine, [422, 409])

    assert service.flush_workflow() == 0
    status, detail, attempts, retry_at = _row(engine)
    assert (status, detail, attempts) == ("PENDING", "PEER_REJECTED_422", 1)
    assert retry_at == clock.now() + timedelta(seconds=2)

    # Backoff honored: not redelivered before retry_at.
    clock.advance(1)
    assert service.flush_workflow() == 0
    assert peer.calls == 1

    clock.advance(1)
    assert service.flush_workflow() == 0
    status, detail, attempts, retry_at = _row(engine)
    assert (status, detail, attempts) == ("PENDING", "PEER_REJECTED_409", 2)
    assert retry_at == clock.now() + timedelta(seconds=4)  # exponential

    clock.advance(4)
    assert service.flush_workflow() == 1
    assert peer.calls == 3
    assert _row(engine)[0] == "DELIVERED"


@pytest.mark.parametrize(
    ("status_code", "code"),
    [
        (403, "PEER_UNAUTHORIZED"),
        (401, "PEER_UNAUTHORIZED"),
        (404, "PEER_MALFORMED"),
        (400, "PEER_MALFORMED"),
    ],
)
def test_permanent_rejection_not_retried(engine, status_code, code):
    service, peer, clock = _setup(engine, [status_code])

    assert service.flush_workflow() == 0
    status, detail, attempts, _ = _row(engine)
    assert (status, detail, attempts) == ("FAILED", code, 0)

    clock.advance(3600)
    assert service.flush_workflow() == 0
    assert peer.calls == 1


def test_transient_rejection_fails_after_max_attempts(engine):
    service, peer, clock = _setup(
        engine,
        [429, 429, 422],
        workflow_retry_max_attempts=3,
        workflow_retry_base_seconds=10,
        workflow_retry_max_seconds=15,
    )

    assert service.flush_workflow() == 0
    assert _row(engine)[3] == clock.now() + timedelta(seconds=10)
    clock.advance(10)
    assert service.flush_workflow() == 0
    assert _row(engine)[3] == clock.now() + timedelta(seconds=15)  # capped
    clock.advance(15)
    assert service.flush_workflow() == 0

    status, detail, attempts, retry_at = _row(engine)
    assert (status, detail, attempts, retry_at) == ("FAILED", "PEER_REJECTED_422", 3, None)
    clock.advance(3600)
    assert service.flush_workflow() == 0
    assert peer.calls == 3


def test_peer_unavailable_still_retried_immediately(engine):
    service, peer, _ = _setup(engine, [503])

    assert service.flush_workflow() == 0
    status, detail, attempts, retry_at = _row(engine)
    assert (status, detail, attempts, retry_at) == ("PENDING", "PEER_UNAVAILABLE", 0, None)
    assert service.flush_workflow() == 1
    assert peer.calls == 2
