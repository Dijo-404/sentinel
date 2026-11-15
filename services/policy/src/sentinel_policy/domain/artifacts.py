"""Versioned policy artifact metadata (list surface; not evaluate rules)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PolicyArtifact:
    policy_id: str
    version: str
    status: str
    updated_at: str

    def as_dict(self) -> dict[str, str]:
        return {
            "policy_id": self.policy_id,
            "version": self.version,
            "status": self.status,
            "updated_at": self.updated_at,
        }
