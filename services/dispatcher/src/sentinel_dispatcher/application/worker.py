"""Dispatch and recovery use cases. Never mints a second provider_ref."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from sentinel_dispatcher.application.ports import Clock, LedgerPort, ProviderPort, WorkerStore
from sentinel_dispatcher.domain.decisions import (
    after_accepted_refund,
    after_lookup,
    after_provider_timeout,
    plan_recovery,
)
from sentinel_dispatcher.domain.types import (
    Command,
    DispatchJob,
    DomainError,
    OutcomeRequest,
    PeerError,
    ProviderCapabilities,
    ProviderTimeout,
    Refund,
    RefundRequest,
)
from sentinel_dispatcher.domain.validate import outcome_event_key, refund_evidence, validate_command


class DispatchWorker:
    def __init__(
        self,
        *,
        tenant_id: str,
        ledger: LedgerPort,
        provider: ProviderPort,
        store: WorkerStore,
        clock: Clock,
    ) -> None:
        self._tenant_id = tenant_id
        self._ledger = ledger
        self._provider = provider
        self._store = store
        self._clock = clock

    def run_once(self, *, limit: int = 1) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for command in self._ledger.claim(limit=limit):
            results.append(self.process_command(command))
        return results

    def recover(self) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for job in self._store.list_incomplete(self._tenant_id):
            results.append(self.recover_job(job))
        return results

    def process_command(self, command: Command) -> dict[str, Any]:
        request = validate_command(command, now=self._clock.now())
        existing = self._store.get(self._tenant_id, command.action_id)
        if existing and existing.phase in {"OUTCOME_REPORTED", "ESCALATED"}:
            return {
                "action_id": command.action_id,
                "provider_ref": command.provider_ref,
                "status": existing.outcome_status,
                "reason_code": existing.reason_code or "ALREADY_COMPLETE",
            }
        job = DispatchJob(
            tenant_id=self._tenant_id,
            action_id=command.action_id,
            provider_ref=command.provider_ref,
            lease_id=command.lease_id,
            action_digest=command.action_digest,
            payload=dict(command.payload),
            phase="CLAIMED",
            same_key_retry=command.provider_capabilities.same_key_retry,
            status_lookup=command.provider_capabilities.status_lookup,
        )
        self._store.save(job)
        return self._dispatch(job, command, request_action_id=request.action_id)

    def recover_job(self, job: DispatchJob) -> dict[str, Any]:
        caps = ProviderCapabilities(
            same_key_retry=job.same_key_retry,
            status_lookup=job.status_lookup,
        )
        plan = plan_recovery(
            phase=job.phase,
            capabilities=caps,
            outcome_status=job.outcome_status,
        )
        if plan.action == "noop":
            return {
                "action_id": job.action_id,
                "provider_ref": job.provider_ref,
                "status": job.outcome_status,
                "reason_code": plan.reason_code,
            }
        if plan.action == "escalate":
            return self._report(
                job,
                status="ESCALATED",
                reason_code=plan.reason_code,
                terminal_phase="ESCALATED",
            )
        if plan.action == "lookup":
            return self._reconcile_lookup(job, caps, reason_code=plan.reason_code)
        # resubmit_same_ref — Idempotency-Key remains the original provider_ref only.
        command = self._command_from_job(job)
        return self._dispatch(job, command, request_action_id=job.action_id)

    def _dispatch(
        self,
        job: DispatchJob,
        command: Command,
        *,
        request_action_id: str,
    ) -> dict[str, Any]:
        del request_action_id  # validated earlier; kept for call-site clarity
        request = RefundRequest.from_command(command)
        # Hard invariant: never invent or rotate the provider reference.
        if request.provider_ref != job.provider_ref or request.provider_ref != command.provider_ref:
            raise DomainError(
                "REFERENCE_MISMATCH",
                "Refusing to dispatch with a substituted provider_ref",
            )
        try:
            refund = self._provider.create_refund(
                request,
                idempotency_key=job.provider_ref,
            )
        except ProviderTimeout:
            submitted = replace(job, phase="SUBMITTED", reason_code="PROVIDER_TIMEOUT")
            self._store.save(submitted)
            decision = after_provider_timeout(command.provider_capabilities)
            reported = self._report(
                submitted,
                status=decision.status,
                reason_code=decision.reason_code,
                terminal_phase=(
                    "ESCALATED" if decision.status == "ESCALATED" else "OUTCOME_REPORTED"
                ),
            )
            if decision.status == "OUTCOME_UNKNOWN" and command.provider_capabilities.status_lookup:
                latest = self._store.get(self._tenant_id, job.action_id) or submitted
                return self._reconcile_lookup(
                    latest,
                    command.provider_capabilities,
                    reason_code="POST_TIMEOUT_LOOKUP",
                )
            if (
                decision.status == "OUTCOME_UNKNOWN"
                and decision.may_resubmit
                and command.provider_capabilities.same_key_retry
            ):
                # Safe same-key retry still uses the original provider_ref only.
                try:
                    refund = self._provider.create_refund(
                        request,
                        idempotency_key=job.provider_ref,
                    )
                except ProviderTimeout:
                    return reported
                return self._accept(job=submitted, refund=refund, lease_id=command.lease_id)
            return reported
        except PeerError as exc:
            if exc.code in {"UNAUTHORIZED", "FORBIDDEN", "OUT_OF_SCOPE"}:
                raise
            submitted = replace(job, phase="SUBMITTED", reason_code=exc.code)
            self._store.save(submitted)
            return self._report(
                submitted,
                status="OUTCOME_UNKNOWN",
                reason_code=exc.code,
                terminal_phase="OUTCOME_REPORTED",
            )

        return self._accept(job=job, refund=refund, lease_id=command.lease_id)

    def _accept(self, *, job: DispatchJob, refund: Refund, lease_id: str) -> dict[str, Any]:
        if refund.provider_ref != job.provider_ref or refund.action_id != job.action_id:
            raise DomainError(
                "PROVIDER_REFERENCE_MISMATCH",
                "Provider response references do not match the ledger command",
            )
        submitted = replace(
            job,
            phase="SUBMITTED",
            provider_status=refund.status,
        )
        self._store.save(submitted)
        decision = after_accepted_refund(refund)
        return self._report(
            submitted,
            status=decision.status,
            reason_code=decision.reason_code,
            terminal_phase="OUTCOME_REPORTED",
            refund=refund,
            lease_id=lease_id,
        )

    def _reconcile_lookup(
        self,
        job: DispatchJob,
        caps: ProviderCapabilities,
        *,
        reason_code: str,
    ) -> dict[str, Any]:
        del reason_code
        try:
            refund = self._provider.get_refund(job.provider_ref)
            not_found = refund is None
        except PeerError as exc:
            if exc.status_code == 404 or exc.code == "NOT_FOUND":
                refund = None
                not_found = True
            else:
                return self._report(
                    job,
                    status="ESCALATED",
                    reason_code="LOOKUP_UNAVAILABLE_PRESERVE_RESERVATION",
                    terminal_phase="ESCALATED",
                )
        decision = after_lookup(
            capabilities=caps,
            refund=refund,
            lookup_not_found=not_found,
        )
        if decision.may_resubmit and caps.same_key_retry:
            command = self._command_from_job(job)
            try:
                refund = self._provider.create_refund(
                    RefundRequest.from_command(command),
                    idempotency_key=job.provider_ref,
                )
            except ProviderTimeout:
                return self._report(
                    job,
                    status="OUTCOME_UNKNOWN",
                    reason_code="RETRY_TIMEOUT_PRESERVE_RESERVATION",
                    terminal_phase="OUTCOME_REPORTED",
                )
            return self._accept(job=job, refund=refund, lease_id=job.lease_id)
        phase = "ESCALATED" if decision.status == "ESCALATED" else "OUTCOME_REPORTED"
        return self._report(
            job,
            status=decision.status,
            reason_code=decision.reason_code,
            terminal_phase=phase,
            refund=refund,
        )

    def _report(
        self,
        job: DispatchJob,
        *,
        status: str,
        reason_code: str,
        terminal_phase: str,
        refund: Refund | None = None,
        lease_id: str | None = None,
    ) -> dict[str, Any]:
        evidence: list[dict[str, Any]] = []
        if refund is not None:
            evidence.append(
                refund_evidence(
                    {
                        "action_id": refund.action_id,
                        "provider_ref": refund.provider_ref,
                        "transaction_ref": refund.transaction_ref,
                        "amount_minor": refund.amount_minor,
                        "currency": refund.currency,
                        "status": refund.status,
                    },
                    evidence_id=f"evidence-dispatch-{job.action_id}",
                    case_id=str(job.payload["case_id"]),
                )
            )
        outcome = OutcomeRequest(
            event_key=outcome_event_key(job.action_id, status),
            status=status,  # type: ignore[arg-type]
            evidence=tuple(evidence),
            reason_code=reason_code,
            lease_id=lease_id or job.lease_id,
        )
        self._ledger.report_outcome(job.action_id, outcome)
        saved = replace(
            job,
            phase=terminal_phase,  # type: ignore[arg-type]
            outcome_status=status,
            reason_code=reason_code,
            provider_status=refund.status if refund is not None else job.provider_status,
        )
        self._store.save(saved)
        return {
            "action_id": job.action_id,
            "provider_ref": job.provider_ref,
            "status": status,
            "reason_code": reason_code,
        }

    def _command_from_job(self, job: DispatchJob) -> Command:
        return Command(
            action_id=job.action_id,
            provider_ref=job.provider_ref,
            payload=dict(job.payload),
            action_digest=job.action_digest,
            lease_id=job.lease_id,
            lease_expires_at="2099-01-01T00:00:00Z",
            provider_capabilities=ProviderCapabilities(
                same_key_retry=job.same_key_retry,
                status_lookup=job.status_lookup,
            ),
        )
