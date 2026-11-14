"""Framework-free wire-aligned types for assistant.v1."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

CONTRACT_VERSION = "sentinel.task-contracts.v1"
PORT_NAME = "assistant.v1"
COMPONENT = "assistant"

ThreadAudience = Literal["customer", "operator"]
MessageRole = Literal["user", "assistant", "system"]
THREAD_AUDIENCES = ("customer", "operator")


@dataclass(frozen=True, slots=True)
class Principal:
    principal_id: str
    tenant_id: str
    roles: tuple[str, ...]

    def thread_audience(self) -> ThreadAudience:
        if "customer" in self.roles:
            return "customer"
        if "operator" in self.roles or "supervisor" in self.roles:
            return "operator"
        raise ValueError("Principal has no customer or operator audience role")

    def allows_audience(self, audience: ThreadAudience) -> bool:
        if audience == "customer":
            return "customer" in self.roles
        return "operator" in self.roles or "supervisor" in self.roles


@dataclass(frozen=True, slots=True)
class Thread:
    thread_id: str
    tenant_id: str
    role: ThreadAudience
    title: str
    created_at: str
    updated_at: str
    created_by: str

    def to_wire(self) -> dict[str, Any]:
        return {
            "thread_id": self.thread_id,
            "title": self.title,
            "updated_at": self.updated_at,
            "role": self.role,
        }


@dataclass(frozen=True, slots=True)
class Message:
    message_id: str
    thread_id: str
    tenant_id: str
    role: MessageRole
    text: str
    evidence_mode: str
    created_at: str
    principal_id: str | None = None

    def to_wire(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "role": self.role,
            "text": self.text,
            "evidence_mode": self.evidence_mode,
            "created_at": self.created_at,
        }
