"""In-memory assistant store for fixture mode and unit tests."""

from __future__ import annotations

import threading

from ..domain.types import Message, Thread, ThreadAudience


class MemoryAssistantStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._threads: dict[str, Thread] = {}
        self._messages: dict[str, list[Message]] = {}

    def create_thread(self, thread: Thread) -> Thread:
        with self._lock:
            self._threads[thread.thread_id] = thread
            self._messages.setdefault(thread.thread_id, [])
            return thread

    def list_threads(self, *, tenant_id: str, role: ThreadAudience) -> tuple[Thread, ...]:
        items = [t for t in self._threads.values() if t.tenant_id == tenant_id and t.role == role]
        return tuple(sorted(items, key=lambda t: t.updated_at, reverse=True))

    def get_thread(self, thread_id: str) -> Thread | None:
        return self._threads.get(thread_id)

    def touch_thread(self, thread_id: str, *, updated_at: str) -> Thread:
        with self._lock:
            current = self._threads[thread_id]
            updated = Thread(
                thread_id=current.thread_id,
                tenant_id=current.tenant_id,
                role=current.role,
                title=current.title,
                created_at=current.created_at,
                updated_at=updated_at,
                created_by=current.created_by,
            )
            self._threads[thread_id] = updated
            return updated

    def add_message(self, message: Message) -> Message:
        with self._lock:
            self._messages.setdefault(message.thread_id, []).append(message)
            return message

    def list_messages(self, *, thread_id: str, tenant_id: str) -> tuple[Message, ...]:
        items = [m for m in self._messages.get(thread_id, []) if m.tenant_id == tenant_id]
        return tuple(sorted(items, key=lambda m: m.created_at))

    def upsert_seed_bundle(self, thread: Thread, messages: tuple[Message, ...]) -> None:
        with self._lock:
            self._threads[thread.thread_id] = thread
            self._messages[thread.thread_id] = list(messages)
