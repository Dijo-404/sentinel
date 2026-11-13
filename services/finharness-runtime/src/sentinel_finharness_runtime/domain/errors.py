"""Explicit failure types. Messages never include secrets or credentials."""

from __future__ import annotations

from typing import Literal

PeerName = Literal[
    "finharness-sdk.v1",
    "indic-context.v1",
    "evidence.v1",
    "policy.v1",
    "action-ledger.v1",
    "verifier.v1",
]


class ConfigurationError(ValueError):
    """Unsafe or incomplete runtime configuration."""


class CapabilityDenied(PermissionError):
    """Routing, write, notification, or sandbox capability not explicitly enabled."""


class ContractViolation(ValueError):
    """Payload failed local contract shape checks."""


class SafetyViolation(PermissionError):
    """Shadow/sandbox safety guard blocked a write, credential, or notification."""


class PeerError(RuntimeError):
    """Injected peer unavailable, malformed, unauthorized, or out of scope."""

    def __init__(self, peer: PeerName, code: str, message: str) -> None:
        self.peer = peer
        self.code = code
        super().__init__(f"{peer}: {code}: {message}")
