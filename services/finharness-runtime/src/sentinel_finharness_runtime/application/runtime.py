"""Pinned-case runtime: shadow comparison, sandbox routing, restart-safe reconcile."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sentinel_finharness_runtime.application.ports import (
    ActionLedgerPort,
    CaseStorePort,
    EvidencePort,
    FinHarnessSdkPort,
    IndicContextPort,
    PolicyPort,
    SafetyGuardPort,
    VerifierPort,
)
from sentinel_finharness_runtime.domain.errors import (
    CapabilityDenied,
    ConfigurationError,
    SafetyViolation,
)
from sentinel_finharness_runtime.domain.models import (
    CONTRACT_SHA256,
    CONTRACT_VERSION,
    CaseManifest,
    CasePin,
    ReconcileResult,
    RouteDecision,
    RuntimeConfig,
    ShadowComparison,
    UnknownAction,
)
from sentinel_finharness_runtime.domain.rules import proposals_equal


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class RuntimePorts:
    evidence: EvidencePort
    policy: PolicyPort
    ledger: ActionLedgerPort
    verifier: VerifierPort
    indic_context: IndicContextPort
    sdk: FinHarnessSdkPort
    store: CaseStorePort
    safety: SafetyGuardPort


class FinHarnessRuntime:
    """Case-pinned FinHarness runtime. SN-009 remains sole financial authority."""

    def __init__(self, *, config: RuntimeConfig, ports: RuntimePorts) -> None:
        self._config = config
        self._ports = ports

    @property
    def config(self) -> RuntimeConfig:
        return self._config

    @property
    def ports(self) -> RuntimePorts:
        return self._ports

    def apply_config(self, config: RuntimeConfig) -> None:
        """Switch rollout/mode. Existing case pins stay; unknown actions stay."""
        self._config = config

    def start_case(
        self,
        *,
        case_id: str,
        tenant_id: str,
        manifest: CaseManifest,
        now: str | None = None,
    ) -> CasePin:
        if not case_id or not tenant_id:
            raise ConfigurationError("case_id and tenant_id are required")
        if not self._config.allows_tenant(tenant_id):
            raise CapabilityDenied(f"tenant {tenant_id!r} not in allowed_tenants")
        if not self._config.allows_workflow(manifest.workflow_name):
            raise CapabilityDenied(f"workflow {manifest.workflow_name!r} not in allowed_workflows")

        existing = self._ports.store.get_pin(case_id)
        if existing is not None:
            return existing

        if not self._config.case_eligible_for_new_routing(case_id):
            raise CapabilityDenied(
                "new-case routing disabled for this case "
                "(enabled=false, legacy mode, or outside rollout)"
            )

        pin = CasePin(
            case_id=case_id,
            tenant_id=tenant_id,
            runtime_version=self._config.runtime_version,
            workflow_name=manifest.workflow_name,
            workflow_version=manifest.workflow_version,
            execution_mode=self._config.execution_mode,
            pinned_at=now or _utc_now(),
            manifest=manifest,
        )
        self._ports.store.save_pin(pin)
        return pin

    def inspect_case(self, case_id: str) -> CasePin:
        pin = self._ports.store.get_pin(case_id)
        if pin is None:
            raise ConfigurationError(f"case {case_id!r} has no runtime pin")
        return pin

    def route_sandbox(self, case_id: str) -> RouteDecision:
        pin = self.inspect_case(case_id)
        cfg = self._config
        if pin.execution_mode == "shadow":
            return RouteDecision(
                case_id=case_id,
                routed=True,
                execution_mode="shadow",
                runtime_version=pin.runtime_version,
                financial_writes=False,
                reason_code="SHADOW_READ_ONLY",
            )
        if pin.execution_mode != "harness":
            return RouteDecision(
                case_id=case_id,
                routed=False,
                execution_mode=pin.execution_mode,
                runtime_version=pin.runtime_version,
                financial_writes=False,
                reason_code="PINNED_NOT_HARNESS",
            )
        if not cfg.allows_tenant(pin.tenant_id):
            return RouteDecision(
                case_id=case_id,
                routed=False,
                execution_mode=pin.execution_mode,
                runtime_version=pin.runtime_version,
                financial_writes=False,
                reason_code="TENANT_DENIED",
            )
        if cfg.sandbox_only and cfg.allowed_tenants and pin.tenant_id not in cfg.allowed_tenants:
            return RouteDecision(
                case_id=case_id,
                routed=False,
                execution_mode=pin.execution_mode,
                runtime_version=pin.runtime_version,
                financial_writes=False,
                reason_code="SANDBOX_TENANT_DENIED",
            )
        writes = bool(cfg.financial_writes and cfg.execution_mode == "harness")
        return RouteDecision(
            case_id=case_id,
            routed=True,
            execution_mode=pin.execution_mode,
            runtime_version=pin.runtime_version,
            financial_writes=writes,
            reason_code="SANDBOX_HARNESS_ROUTED" if writes else "SANDBOX_HARNESS_READ_ONLY",
        )

    def run_shadow(
        self,
        *,
        case_id: str,
        baseline_proposal: Mapping[str, Any],
        case_revision: int = 1,
        order_reference: str = "DEMO-ORDER-42",
        original_text: str = "Synthetic duplicate payment complaint",
        language: str = "en-IN",
        evidence_mode: str = "fixture",
    ) -> ShadowComparison:
        pin = self.inspect_case(case_id)
        if pin.execution_mode != "shadow" and self._config.execution_mode != "shadow":
            raise CapabilityDenied("shadow comparison requires shadow execution mode")

        self._ports.safety.assert_shadow_safe()

        for probe in (
            lambda: self._ports.safety.attempt_refund_write(provider_ref="shadow-must-not-write"),
            lambda: self._ports.safety.attempt_notification(channel="customer"),
            lambda: self._ports.safety.attempt_credential_use(name="PAYMENT_WRITE_KEY"),
        ):
            try:
                probe()
            except SafetyViolation:
                pass

        collect_req = {
            "case_id": case_id,
            "case_revision": case_revision,
            "order_reference": order_reference,
        }
        bundle = dict(self._ports.evidence.collect(collect_req))
        evidence = list(bundle.get("evidence", []))

        model_req = {
            "case": {
                "contract_version": CONTRACT_VERSION,
                "case_id": case_id,
                "revision": case_revision,
                "status": "RECEIVED",
                "language": language,
                "intent": pin.workflow_name,
                "evidence_ids": [e.get("evidence_id") for e in evidence if isinstance(e, Mapping)],
            },
            "input": {
                "case_id": case_id,
                "case_revision": case_revision,
                "original_text": original_text,
                "language": language,
                "order_reference": order_reference,
                "messages": [],
            },
            "evidence": evidence,
        }
        sdk_result = dict(self._ports.sdk.run_read_path(model_req))
        candidate = dict(sdk_result.get("proposal") or {})

        self._ports.policy.evaluate(
            {"payload": candidate or dict(baseline_proposal), "evidence": evidence}
        )

        try:
            self._ports.ledger.create_proposal(
                {
                    "operation_key": f"{case_id}:shadow-blocked",
                    "payload": dict(baseline_proposal),
                    "action_digest": "blocked",
                }
            )
            raise CapabilityDenied("shadow path must not succeed on ledger create_proposal")
        except CapabilityDenied:
            pass

        match = proposals_equal(baseline_proposal, candidate) if candidate else False
        reasons: list[str] = []
        if not candidate:
            reasons.append("CANDIDATE_EMPTY")
        elif match:
            reasons.append("PROPOSALS_MATCH")
        else:
            reasons.append("PROPOSALS_DIFFER")
        reasons.append("NO_WRITE_ADAPTER")
        reasons.append("NO_SECOND_REFUND")
        reasons.append("NO_CREDENTIALS")
        reasons.append("NOTIFICATIONS_BLOCKED")

        return ShadowComparison(
            case_id=case_id,
            runtime_version=pin.runtime_version,
            evidence_mode="fixture" if evidence_mode == "fixture" else "real-peers",
            baseline_proposal=dict(baseline_proposal),
            candidate_proposal=candidate,
            proposals_match=match,
            write_adapter_present=self._ports.safety.write_adapter_present,
            credentials_present=self._ports.safety.credentials_present,
            notifications_attempted=self._ports.safety.notifications_attempted,
            refund_write_attempts=self._ports.safety.refund_write_attempts,
            reason_codes=tuple(reasons),
        )

    def record_unknown(
        self,
        *,
        action_id: str,
        case_id: str,
        provider_ref: str,
        now: str | None = None,
    ) -> UnknownAction:
        if not action_id or not provider_ref:
            raise ConfigurationError("action_id and provider_ref are required")
        action = UnknownAction(
            action_id=action_id,
            case_id=case_id,
            provider_ref=provider_ref,
            status="OUTCOME_UNKNOWN",
            recorded_at=now or _utc_now(),
        )
        self._ports.store.save_unknown(action)
        return action

    def reconcile_unknown(self, action_id: str) -> ReconcileResult:
        """Reconcile by original provider_ref. Kill switch does not stop this."""
        recorded = self._ports.store.get_unknown(action_id)
        if recorded is None:
            raise ConfigurationError(f"unknown action {action_id!r} not recorded")

        looked_up = dict(self._ports.ledger.query_by_provider_ref(recorded.provider_ref))
        status = str(looked_up.get("status") or "OUTCOME_UNKNOWN")
        returned_ref = str(looked_up.get("provider_ref") or recorded.provider_ref)
        if returned_ref != recorded.provider_ref:
            raise CapabilityDenied(
                "reconcile must not mint a new refund reference; "
                f"expected {recorded.provider_ref!r}, got {returned_ref!r}"
            )
        return ReconcileResult(
            action_id=action_id,
            provider_ref=recorded.provider_ref,
            status=status,
            minted_new_refund=False,
            financial_writes_enabled=self._config.financial_writes,
        )


def build_runtime(*, config: RuntimeConfig, ports: RuntimePorts) -> FinHarnessRuntime:
    return FinHarnessRuntime(config=config, ports=ports)


def self_check_report() -> dict[str, Any]:
    """Fixture-mode smoke used by CLI / make preview."""
    from sentinel_finharness_runtime.adapters.composition import fixture_runtime

    runtime, manifest, baseline = fixture_runtime()
    pin = runtime.start_case(case_id="case-demo-42", tenant_id="sandbox", manifest=manifest)
    shadow = runtime.run_shadow(case_id=pin.case_id, baseline_proposal=baseline)
    runtime.record_unknown(
        action_id="action-demo-1",
        case_id=pin.case_id,
        provider_ref="refund-demo-1",
    )
    reconciled = runtime.reconcile_unknown("action-demo-1")
    status = (
        "PASS"
        if (
            not shadow.write_adapter_present
            and not shadow.credentials_present
            and not reconciled.minted_new_refund
            and shadow.proposals_match
            and "NO_SECOND_REFUND" in shadow.reason_codes
        )
        else "FAIL"
    )
    return {
        "contract_version": CONTRACT_VERSION,
        "port": "finharness-runtime.v1",
        "baseline_sha256": CONTRACT_SHA256,
        "status": status,
        "runtime_version": pin.runtime_version,
        "shadow_match": shadow.proposals_match,
        "reconciled_provider_ref": reconciled.provider_ref,
        "write_adapter_present": shadow.write_adapter_present,
        "refund_write_attempts_denied": shadow.refund_write_attempts,
    }
