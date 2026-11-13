"""Acceptance: timeout/crash recovery and invalid/ambiguous command handling."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from sentinel_dispatcher.adapters.clock import FixedClock
from sentinel_dispatcher.adapters.memory_store import MemoryWorkerStore
from sentinel_dispatcher.application.worker import DispatchWorker
from sentinel_dispatcher.domain.types import (
    Command,
    DispatchJob,
    DomainError,
    PeerError,
    Refund,
    RefundRequest,
)
from tests.conftest import NOW, TENANT
from tests.stubs.ledger import StubLedger
from tests.stubs.provider import StubProvider


def _worker(
    command: Command,
    *,
    provider_mode: str = "valid",
    store=None,
    clock: FixedClock | None = None,
):
    ledger = StubLedger([command], tenant_id=TENANT)
    provider = StubProvider(mode=provider_mode)  # type: ignore[arg-type]
    store = store or MemoryWorkerStore()
    worker = DispatchWorker(
        tenant_id=TENANT,
        ledger=ledger,
        provider=provider,
        store=store,
        clock=clock or FixedClock(NOW),
    )
    return worker, ledger, provider, store


def test_happy_path_reports_pending_with_original_refs(demo_command: Command) -> None:
    worker, ledger, provider, _ = _worker(demo_command)
    results = worker.run_once(limit=1)
    assert results == [
        {
            "action_id": "action-demo-1",
            "provider_ref": "refund-demo-1",
            "status": "PENDING",
            "reason_code": "PROVIDER_ACCEPTED",
        }
    ]
    assert provider.side_effect_count("refund-demo-1") == 1
    assert provider.create_calls[0]["idempotency_key"] == "refund-demo-1"
    assert ledger.outcomes[-1]["status"] == "PENDING"
    assert ledger.reservation_held("action-demo-1")


def test_commit_then_timeout_reconciles_original_ref_one_side_effect(
    demo_command: Command,
) -> None:
    worker, ledger, provider, _ = _worker(demo_command, provider_mode="commit_then_timeout")
    result = worker.process_command(demo_command)
    assert result["provider_ref"] == "refund-demo-1"
    assert result["action_id"] == "action-demo-1"
    assert result["status"] == "PENDING"
    assert provider.side_effect_count() == 1
    assert provider.side_effect_count("refund-demo-1") == 1
    assert provider.lookup_calls == ["refund-demo-1"]
    assert all(call["idempotency_key"] == "refund-demo-1" for call in provider.create_calls)
    assert ledger.reservation_held("action-demo-1")
    # Never invent a second refund reference.
    assert set(provider.refunds) == {"refund-demo-1"}


def test_crash_restart_uses_durable_original_refs_one_side_effect(
    demo_command: Command,
    pg_store,
) -> None:
    provider = StubProvider(mode="commit_then_timeout")
    ledger = StubLedger(tenant_id=TENANT)
    # Simulate crash after provider commit but before outcome report.
    job = DispatchJob(
        tenant_id=TENANT,
        action_id=demo_command.action_id,
        provider_ref=demo_command.provider_ref,
        lease_id=demo_command.lease_id,
        action_digest=demo_command.action_digest,
        payload=dict(demo_command.payload),
        phase="SUBMITTED",
        same_key_retry=True,
        status_lookup=True,
        reason_code="CRASH_AFTER_COMMIT",
    )
    # Seed the simulated committed refund under the original reference only.
    provider.refunds[demo_command.provider_ref] = Refund(
        action_id=demo_command.action_id,
        provider_ref=demo_command.provider_ref,
        transaction_ref=str(demo_command.payload["transaction_ref"]),
        amount_minor=int(demo_command.payload["amount_minor"]),
        currency="INR",
        status="PENDING",
    )
    provider.side_effects.append(demo_command.provider_ref)
    pg_store.save(job)
    ledger.actions[demo_command.action_id] = {
        "action_id": demo_command.action_id,
        "provider_ref": demo_command.provider_ref,
        "payload": dict(demo_command.payload),
        "action_digest": demo_command.action_digest,
        "status": "DISPATCHING",
    }
    ledger.reservations_held.add(demo_command.action_id)

    restarted = DispatchWorker(
        tenant_id=TENANT,
        ledger=ledger,
        provider=provider,
        store=pg_store,
        clock=FixedClock(NOW),
    )
    results = restarted.recover()
    assert len(results) == 1
    assert results[0]["provider_ref"] == "refund-demo-1"
    assert results[0]["action_id"] == "action-demo-1"
    assert results[0]["status"] == "PENDING"
    assert provider.side_effect_count() == 1
    assert set(provider.refunds) == {"refund-demo-1"}
    assert ledger.reservation_held("action-demo-1")
    saved = pg_store.get(TENANT, demo_command.action_id)
    assert saved is not None
    assert saved.phase == "OUTCOME_REPORTED"
    assert saved.provider_ref == "refund-demo-1"


def test_expired_lease_fails_without_provider_write(demo_command: Command) -> None:
    expired = replace(demo_command, lease_expires_at="2026-11-13T11:59:59Z")
    worker, ledger, provider, _ = _worker(expired)
    with pytest.raises(DomainError) as exc:
        worker.process_command(expired)
    assert exc.value.code == "LEASE_EXPIRED"
    assert provider.side_effect_count() == 0
    assert ledger.outcomes == []
    assert ledger.reservation_held("action-demo-1")


def test_digest_mismatch_fails_without_provider_write(demo_command: Command) -> None:
    bad = replace(demo_command, action_digest="0" * 64)
    worker, _, provider, _ = _worker(bad)
    with pytest.raises(DomainError) as exc:
        worker.process_command(bad)
    assert exc.value.code == "DIGEST_MISMATCH"
    assert provider.side_effect_count() == 0


def test_mismatched_payload_fields_fail(demo_command: Command) -> None:
    payload = deepcopy(dict(demo_command.payload))
    payload["amount_minor"] = 1
    bad = replace(demo_command, payload=payload)
    worker, _, provider, _ = _worker(bad)
    with pytest.raises(DomainError) as exc:
        worker.process_command(bad)
    assert exc.value.code == "DIGEST_MISMATCH"
    assert provider.side_effect_count() == 0


def test_ambiguous_non_idempotent_escalates_preserves_reservation(
    demo_command: Command,
) -> None:
    caps = replace(
        demo_command.provider_capabilities,
        same_key_retry=False,
        status_lookup=False,
    )
    command = replace(demo_command, provider_capabilities=caps)
    worker, ledger, provider, _ = _worker(command, provider_mode="commit_then_timeout")
    result = worker.process_command(command)
    assert result["status"] == "ESCALATED"
    assert result["provider_ref"] == "refund-demo-1"
    assert provider.side_effect_count() == 1
    assert set(provider.refunds) == {"refund-demo-1"}
    assert ledger.reservation_held("action-demo-1")
    assert ledger.outcomes[-1]["reason_code"] == "PROVIDER_AMBIGUOUS_NO_SAFE_RETRY"


def test_lookup_404_without_safe_retry_escalates_preserves_reservation(
    demo_command: Command,
) -> None:
    caps = replace(
        demo_command.provider_capabilities,
        same_key_retry=False,
        status_lookup=True,
    )
    command = replace(demo_command, provider_capabilities=caps)
    provider = StubProvider(mode="ambiguous_not_found")
    # Pretend a prior write may have happened under the original ref; lookup stays ambiguous.
    store = MemoryWorkerStore()
    job = DispatchJob(
        tenant_id=TENANT,
        action_id=command.action_id,
        provider_ref=command.provider_ref,
        lease_id=command.lease_id,
        action_digest=command.action_digest,
        payload=dict(command.payload),
        phase="SUBMITTED",
        same_key_retry=False,
        status_lookup=True,
    )
    store.save(job)
    ledger = StubLedger(tenant_id=TENANT)
    ledger.actions[command.action_id] = {
        "action_id": command.action_id,
        "provider_ref": command.provider_ref,
        "payload": dict(command.payload),
        "action_digest": command.action_digest,
        "status": "DISPATCHING",
    }
    ledger.reservations_held.add(command.action_id)
    worker = DispatchWorker(
        tenant_id=TENANT,
        ledger=ledger,
        provider=provider,
        store=store,
        clock=FixedClock(NOW),
    )
    result = worker.recover_job(job)
    assert result["status"] == "ESCALATED"
    assert result["provider_ref"] == "refund-demo-1"
    assert provider.create_calls == []
    assert ledger.reservation_held("action-demo-1")


def test_lease_expiry_never_releases_reservation(demo_command: Command) -> None:
    """Even after an expired lease is refused, ledger reservation authority remains."""
    expired = replace(demo_command, lease_expires_at="2026-11-13T11:00:00Z")
    ledger = StubLedger([expired], tenant_id=TENANT)
    assert ledger.reservation_held("action-demo-1")
    worker = DispatchWorker(
        tenant_id=TENANT,
        ledger=ledger,
        provider=StubProvider(),
        store=MemoryWorkerStore(),
        clock=FixedClock(datetime(2026, 11, 13, 12, 0, tzinfo=UTC)),
    )
    with pytest.raises(DomainError):
        worker.process_command(expired)
    assert ledger.reservation_held("action-demo-1")


@pytest.mark.parametrize(
    "mode",
    ["unavailable", "malformed", "unauthorized_or_out_of_scope"],
)
def test_ledger_stub_modes(demo_command: Command, mode: str) -> None:
    ledger = StubLedger([demo_command], mode=mode)  # type: ignore[arg-type]
    with pytest.raises(PeerError):
        ledger.claim(limit=1)


@pytest.mark.parametrize(
    "mode",
    ["unavailable", "malformed", "unauthorized_or_out_of_scope"],
)
def test_provider_stub_modes(demo_command: Command, mode: str) -> None:
    provider = StubProvider(mode=mode)  # type: ignore[arg-type]
    request = RefundRequest.from_command(demo_command)
    with pytest.raises(PeerError):
        provider.create_refund(request, idempotency_key=demo_command.provider_ref)
