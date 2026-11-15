"""Narrow ports for assistant persistence and time."""

from __future__ import annotations

from typing import Protocol

from ..domain.types import Message, Thread, ThreadAudience


class Clock(Protocol):
    def now_iso(self) -> str: ...


class ReplyGenerator(Protocol):
    """Produces assistant reply text + evidence_mode. Never invents money authority."""

    def generate(self, *, text: str) -> tuple[str, str]:
        """Return (reply_text, evidence_mode)."""


class AssistantStore(Protocol):
    def create_thread(self, thread: Thread) -> Thread: ...

    def list_threads(self, *, tenant_id: str, role: ThreadAudience) -> tuple[Thread, ...]: ...

    def get_thread(self, thread_id: str) -> Thread | None: ...

    def touch_thread(self, thread_id: str, *, updated_at: str) -> Thread: ...

    def add_message(self, message: Message) -> Message: ...

    def list_messages(self, *, thread_id: str, tenant_id: str) -> tuple[Message, ...]: ...

    def upsert_seed_bundle(self, thread: Thread, messages: tuple[Message, ...]) -> None: ...
