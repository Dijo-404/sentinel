"""Narrow injected ports. Implementations live in adapters or test stubs."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from sentinel_finharness_runtime.domain.models import CasePin, UnknownAction


@runtime_checkable
class EvidencePort(Protocol):
    def collect(self, request: Mapping[str, Any]) -> Mapping[str, Any]: ...


@runtime_checkable
class PolicyPort(Protocol):
    def evaluate(self, request: Mapping[str, Any]) -> Mapping[str, Any]: ...


@runtime_checkable
class ActionLedgerPort(Protocol):
    def create_proposal(self, request: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def reserve(self, request: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def get_action(self, action_id: str) -> Mapping[str, Any]: ...

    def query_by_provider_ref(self, provider_ref: str) -> Mapping[str, Any]: ...


@runtime_checkable
class VerifierPort(Protocol):
    def assess(self, request: Mapping[str, Any]) -> Mapping[str, Any]: ...


@runtime_checkable
class IndicContextPort(Protocol):
    def propose(self, request: Mapping[str, Any]) -> Mapping[str, Any]: ...


@runtime_checkable
class FinHarnessSdkPort(Protocol):
    """SDK-compatible facade. Runtime never imports sibling package source."""

    def run_read_path(self, request: Mapping[str, Any]) -> Mapping[str, Any]: ...


@runtime_checkable
class CaseStorePort(Protocol):
    def save_pin(self, pin: CasePin) -> None: ...

    def get_pin(self, case_id: str) -> CasePin | None: ...

    def save_unknown(self, action: UnknownAction) -> None: ...

    def get_unknown(self, action_id: str) -> UnknownAction | None: ...

    def list_unknown(self) -> tuple[UnknownAction, ...]: ...


@runtime_checkable
class SafetyGuardPort(Protocol):
    """Shadow path: no write adapter, credentials, or notifications."""

    @property
    def write_adapter_present(self) -> bool: ...

    @property
    def credentials_present(self) -> bool: ...

    @property
    def notifications_attempted(self) -> int: ...

    @property
    def refund_write_attempts(self) -> int: ...

    def assert_shadow_safe(self) -> None: ...

    def attempt_refund_write(self, *, provider_ref: str | None = None) -> None: ...

    def attempt_notification(self, *, channel: str) -> None: ...

    def attempt_credential_use(self, *, name: str) -> None: ...
