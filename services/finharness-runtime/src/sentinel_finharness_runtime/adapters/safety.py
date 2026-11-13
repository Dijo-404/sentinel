"""Shadow safety: no write adapter, credentials, or customer notifications."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sentinel_finharness_runtime.domain.errors import CapabilityDenied, SafetyViolation


class ShadowSafetyGuard:
    """Tracks denied write/notify/credential attempts. Never holds write credentials."""

    def __init__(self) -> None:
        self._notifications_attempted = 0
        self._refund_write_attempts = 0

    @property
    def write_adapter_present(self) -> bool:
        return False

    @property
    def credentials_present(self) -> bool:
        return False

    @property
    def notifications_attempted(self) -> int:
        return self._notifications_attempted

    @property
    def refund_write_attempts(self) -> int:
        return self._refund_write_attempts

    def assert_shadow_safe(self) -> None:
        if self.write_adapter_present or self.credentials_present:
            raise SafetyViolation("shadow runtime must not expose write adapters or credentials")

    def attempt_refund_write(self, *, provider_ref: str | None = None) -> None:
        self._refund_write_attempts += 1
        raise SafetyViolation(
            f"shadow forbids refund writes (provider_ref={provider_ref!r}); "
            "cannot send a second refund"
        )

    def attempt_notification(self, *, channel: str) -> None:
        self._notifications_attempted += 1
        raise SafetyViolation(f"shadow forbids notifications on channel={channel!r}")

    def attempt_credential_use(self, *, name: str) -> None:
        raise SafetyViolation(f"shadow has no credentials; refused {name!r}")


class ReadOnlyLedger:
    """Wraps a ledger port: reads/reconcile only. Writes raise CapabilityDenied."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner

    def create_proposal(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        _ = request
        raise CapabilityDenied("shadow/read-only ledger forbids create_proposal")

    def reserve(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        _ = request
        raise CapabilityDenied("shadow/read-only ledger forbids reserve")

    def get_action(self, action_id: str) -> Mapping[str, Any]:
        return self._inner.get_action(action_id)

    def query_by_provider_ref(self, provider_ref: str) -> Mapping[str, Any]:
        return self._inner.query_by_provider_ref(provider_ref)
