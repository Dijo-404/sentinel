"""Composition client: contract validation, capability gates, injected peer delegation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .config import RuntimeConfig
from .contracts import (
    CapabilityDenied,
    ConfigurationError,
    PeerError,
    validate_action_record,
    validate_evidence_bundle,
    validate_evidence_collect,
    validate_model_request,
    validate_model_result,
    validate_policy_request,
    validate_policy_result,
    validate_proposal_request,
    validate_reservation_request,
    validate_verification_request,
    validate_verification_result,
)
from .manifest import CaseManifest
from .ports import (
    ActionLedgerPort,
    EvidencePort,
    IndicContextPort,
    PolicyPort,
    VerifierPort,
)


class FinHarnessClient:
    """Injectable FinHarness facade. Never owns a ledger, executor, or case store."""

    def __init__(
        self,
        *,
        config: RuntimeConfig,
        manifest: CaseManifest,
        evidence: EvidencePort,
        policy: PolicyPort,
        ledger: ActionLedgerPort,
        verifier: VerifierPort,
        indic_context: IndicContextPort,
        tenant_id: str,
    ) -> None:
        if not tenant_id:
            raise ConfigurationError("tenant_id is required")
        self.config = config
        self.manifest = manifest
        self._evidence = evidence
        self._policy = policy
        self._ledger = ledger
        self._verifier = verifier
        self._indic_context = indic_context
        self.tenant_id = tenant_id
        self._ensure_scope()

    def _ensure_scope(self) -> None:
        if not self.config.allows_tenant(self.tenant_id):
            raise CapabilityDenied(f"tenant {self.tenant_id!r} not in allowed_tenants")
        if not self.config.allows_workflow(self.manifest.workflow_name):
            raise CapabilityDenied(
                f"workflow {self.manifest.workflow_name!r} not in allowed_workflows"
            )

    def _require_routing(self) -> None:
        if not self.config.routing_active():
            raise CapabilityDenied(
                "FinHarness routing disabled (enabled=false or execution_mode=legacy)"
            )

    def _require_financial_writes(self) -> None:
        self._require_routing()
        if self.config.execution_mode == "shadow":
            raise CapabilityDenied("shadow mode forbids financial writes")
        if not self.config.financial_writes:
            raise CapabilityDenied("financial_writes disabled")

    def _require_notifications(self) -> None:
        self._require_routing()
        if not self.config.notifications:
            raise CapabilityDenied("notifications disabled")

    def collect_evidence(self, request: Mapping[str, Any]) -> dict[str, Any]:
        self._require_routing()
        validated = validate_evidence_collect(request)
        try:
            raw = self._evidence.collect(validated)
        except PeerError:
            raise
        except Exception as exc:  # noqa: BLE001 — surface peer failures explicitly
            raise PeerError("evidence.v1", "unavailable", str(exc)) from exc
        return validate_evidence_bundle(raw)

    def evaluate_policy(self, request: Mapping[str, Any]) -> dict[str, Any]:
        self._require_routing()
        validated = validate_policy_request(request)
        try:
            raw = self._policy.evaluate(validated)
        except PeerError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise PeerError("policy.v1", "unavailable", str(exc)) from exc
        return validate_policy_result(raw)

    def propose(self, request: Mapping[str, Any]) -> dict[str, Any]:
        self._require_routing()
        validated = validate_model_request(request)
        try:
            raw = self._indic_context.propose(validated)
        except PeerError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise PeerError("indic-context.v1", "unavailable", str(exc)) from exc
        return validate_model_result(raw)

    def create_proposal(self, request: Mapping[str, Any]) -> dict[str, Any]:
        """Create an unreserved ledger proposal. Does not grant dispatch rights."""
        self._require_financial_writes()
        validated = validate_proposal_request(request)
        try:
            raw = self._ledger.create_proposal(validated)
        except PeerError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise PeerError("action-ledger.v1", "unavailable", str(exc)) from exc
        return validate_action_record(raw)

    def reserve(self, request: Mapping[str, Any]) -> dict[str, Any]:
        """Reserve only through the injected ledger with an explicit approval_id."""
        self._require_financial_writes()
        validated = validate_reservation_request(request)
        try:
            raw = self._ledger.reserve(validated)
        except PeerError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise PeerError("action-ledger.v1", "unavailable", str(exc)) from exc
        return validate_action_record(raw)

    def get_action(self, action_id: str) -> dict[str, Any]:
        self._require_routing()
        if not action_id:
            raise ConfigurationError("action_id is required")
        try:
            raw = self._ledger.get_action(action_id)
        except PeerError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise PeerError("action-ledger.v1", "unavailable", str(exc)) from exc
        return validate_action_record(raw)

    def assess(self, request: Mapping[str, Any]) -> dict[str, Any]:
        self._require_routing()
        validated = validate_verification_request(request)
        try:
            raw = self._verifier.assess(validated)
        except PeerError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise PeerError("verifier.v1", "unavailable", str(exc)) from exc
        return validate_verification_result(raw)

    def notify(self, *, channel: str, message_code: str) -> dict[str, str]:
        """Customer/operator notification. Explicit capability; never a financial write."""
        self._require_notifications()
        if not channel or not message_code:
            raise ConfigurationError("channel and message_code are required")
        return {"status": "queued", "channel": channel, "message_code": message_code}

    def bypass_reserve_without_approval(self, request: Mapping[str, Any]) -> dict[str, Any]:
        """Deliberately unsafe helper surface: always rejected. No ledger call."""
        raise CapabilityDenied(
            "SDK refuses reservation without approval_id; ledger remains sole authority"
        )
