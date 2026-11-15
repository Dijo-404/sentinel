"""Assistant replies must vary with input; not a single canned string."""

from __future__ import annotations

from datetime import UTC, datetime

from sentinel_assistant.adapters.sandbox_reply import SandboxEchoReply
from sentinel_assistant.adapters.storage_memory import MemoryAssistantStore
from sentinel_assistant.application.service import AssistantService
from sentinel_assistant.domain.types import Principal


class FixedClock:
    def __init__(self, instant: datetime | None = None) -> None:
        self._instant = instant or datetime(2026, 11, 15, 10, 0, tzinfo=UTC)

    def now_iso(self) -> str:
        return self._instant.isoformat().replace("+00:00", "Z")


def test_sandbox_replies_differ_for_different_inputs() -> None:
    store = MemoryAssistantStore()
    service = AssistantService(store=store, clock=FixedClock(), replies=SandboxEchoReply())
    principal = Principal(principal_id="p1", tenant_id="tenant-demo", roles=("customer",))
    thread = service.create_thread(principal, title="t")
    service.post_message(principal, thread_id=thread.thread_id, text="First question about refund")
    service.post_message(principal, thread_id=thread.thread_id, text="Second question about status")
    messages = service.list_messages(principal, thread_id=thread.thread_id)
    assistant = [m for m in messages if m.role == "assistant"]
    assert len(assistant) == 2
    assert assistant[0].text != assistant[1].text
    assert "First question" in assistant[0].text
    assert "Second question" in assistant[1].text
    assert all(m.evidence_mode == "sandbox" for m in assistant)
