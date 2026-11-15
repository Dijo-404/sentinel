"""Assistant use cases: threads and messages. No money authority."""

from __future__ import annotations

import uuid

from ..domain.types import Message, Principal, Thread, ThreadAudience
from .errors import NotFoundError, ValidationError
from .ports import AssistantStore, Clock, ReplyGenerator


class AssistantService:
    def __init__(
        self,
        store: AssistantStore,
        clock: Clock,
        *,
        replies: ReplyGenerator,
    ):
        self._store = store
        self._clock = clock
        self._replies = replies

    def create_thread(self, principal: Principal, *, title: str | None) -> Thread:
        try:
            audience = principal.thread_audience()
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        now = self._clock.now_iso()
        thread = Thread(
            thread_id=f"thr-{uuid.uuid4().hex[:16]}",
            tenant_id=principal.tenant_id,
            role=audience,
            title=(title or "New conversation").strip() or "New conversation",
            created_at=now,
            updated_at=now,
            created_by=principal.principal_id,
        )
        return self._store.create_thread(thread)

    def list_threads(self, principal: Principal, *, role: str) -> tuple[Thread, ...]:
        audience = _parse_audience(role)
        if not principal.allows_audience(audience):
            raise ValidationError(f"Principal cannot list {audience} threads")
        return self._store.list_threads(tenant_id=principal.tenant_id, role=audience)

    def list_messages(self, principal: Principal, *, thread_id: str) -> tuple[Message, ...]:
        thread = self._require_thread(principal, thread_id)
        return self._store.list_messages(thread_id=thread.thread_id, tenant_id=principal.tenant_id)

    def post_message(self, principal: Principal, *, thread_id: str, text: str) -> Message:
        body = (text or "").strip()
        if not body:
            raise ValidationError("text is required")
        thread = self._require_thread(principal, thread_id)
        now = self._clock.now_iso()
        user_message = Message(
            message_id=f"msg-{uuid.uuid4().hex[:16]}",
            thread_id=thread.thread_id,
            tenant_id=principal.tenant_id,
            role="user",
            text=body,
            evidence_mode="sandbox",
            created_at=now,
            principal_id=principal.principal_id,
        )
        saved = self._store.add_message(user_message)
        reply_text, evidence_mode = self._replies.generate(text=body)
        reply = Message(
            message_id=f"msg-{uuid.uuid4().hex[:16]}",
            thread_id=thread.thread_id,
            tenant_id=principal.tenant_id,
            role="assistant",
            text=reply_text,
            evidence_mode=evidence_mode,  # type: ignore[arg-type]
            created_at=now,
            principal_id=None,
        )
        self._store.add_message(reply)
        self._store.touch_thread(thread.thread_id, updated_at=now)
        return saved

    def _require_thread(self, principal: Principal, thread_id: str) -> Thread:
        thread = self._store.get_thread(thread_id)
        if thread is None or thread.tenant_id != principal.tenant_id:
            raise NotFoundError("Thread not found")
        if not principal.allows_audience(thread.role):
            raise NotFoundError("Thread not found")
        return thread


def _parse_audience(role: str) -> ThreadAudience:
    value = (role or "").strip().lower()
    if value not in {"customer", "operator"}:
        raise ValidationError("role must be customer or operator")
    return value  # type: ignore[return-value]
