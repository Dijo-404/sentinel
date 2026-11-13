"""Ledger use cases. Network stays outside the reservation transaction."""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from typing import Any

from sentinel_action_ledger.domain.digest import action_digest, canonical_refund_payload
from sentinel_action_ledger.domain.errors import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)
from sentinel_action_ledger.domain.money import (
    apply_reserve,
    release_allocation,
    reserved_or_pending_to_refunded,
    reserved_to_pending,
)
from sentinel_action_ledger.domain.transitions import (
    assert_transition,
    require_evidence_kinds,
    validate_outcome_status,
)
from sentinel_action_ledger.domain.types import (
    COMPLETED_BALANCE_STATES,
    PENDING_BALANCE_STATES,
    ActionRecord,
    Approval,
    ClaimResult,
    EligibilitySnapshot,
    Principal,
)

from .ports import (
    Clock,
    EvidenceItem,
    EvidencePort,
    IdGenerator,
    LedgerStore,
    NetworkProbe,
    PolicyPort,
    StoredAction,
)


def _iso(dt) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _require_roles(principal: Principal, *roles: str) -> None:
    if not any(principal.has_role(role) for role in roles):
        raise ForbiddenError("Role not permitted for this route")


def _scope_case(principal: Principal, case_id: str) -> None:
    if not principal.allows_case(case_id):
        raise ForbiddenError("Case outside principal scope")


class ActionLedgerService:
    def __init__(
        self,
        *,
        store: LedgerStore,
        clock: Clock,
        ids: IdGenerator,
        evidence: EvidencePort,
        policy: PolicyPort,
        network: NetworkProbe,
        lease_seconds: int = 300,
        provider_capabilities: dict[str, bool] | None = None,
    ) -> None:
        self._store = store
        self._clock = clock
        self._ids = ids
        self._evidence = evidence
        self._policy = policy
        self._network = network
        self._lease_seconds = lease_seconds
        self._provider_capabilities = provider_capabilities or {
            "same_key_retry": True,
            "status_lookup": True,
        }

    def propose(
        self, principal: Principal, *, operation_key: str, payload: dict[str, Any], digest: str
    ) -> tuple[ActionRecord, bool]:
        _require_roles(principal, "workflow")
        normalized = canonical_refund_payload(payload)
        expected = action_digest(normalized)
        if digest != expected:
            raise ValidationError("action_digest does not match payload", code="DIGEST_MISMATCH")
        _scope_case(principal, normalized["case_id"])
        now = _iso(self._clock.now())
        with self._store.transaction() as uow:
            existing = uow.get_action_by_operation_key(principal.tenant_id, operation_key)
            if existing is not None:
                if existing.action_digest != expected or existing.payload != normalized:
                    raise ConflictError(
                        "Key already used with a different payload",
                        code="IDEMPOTENCY_CONFLICT",
                    )
                return uow.to_record(existing), False
            action = StoredAction(
                tenant_id=principal.tenant_id,
                action_id=self._ids.new_id("action"),
                operation_key=operation_key,
                provider_ref=self._ids.new_id("refund"),
                payload=normalized,
                action_digest=expected,
                status="PROPOSED",
                amount_minor=normalized["amount_minor"],
                currency=normalized["currency"],
                transaction_ref=normalized["transaction_ref"],
                case_id=normalized["case_id"],
                case_revision=normalized["case_revision"],
                policy_version=normalized["policy_version"],
                approval_id=None,
                lease_id=None,
                lease_expires_at=None,
                created_at=now,
                updated_at=now,
            )
            uow.insert_action(action)
            uow.insert_audit(
                tenant_id=principal.tenant_id,
                action_id=action.action_id,
                event_type="PROPOSED",
                actor_id=principal.principal_id,
                detail={"operation_key": operation_key, "digest": expected},
                occurred_at=now,
            )
            return uow.to_record(action), True

    def decide(
        self,
        principal: Principal,
        *,
        action_id: str,
        decision: str,
        action_digest_value: str,
        case_revision: int,
        policy_version: str,
        expires_at: str,
    ) -> Approval:
        _require_roles(principal, "supervisor")
        if decision not in {"APPROVE", "REJECT"}:
            raise ValidationError("decision must be APPROVE or REJECT")
        now = self._clock.now()
        if expires_at <= _iso(now):
            raise ValidationError("expires_at must be in the future")
        with self._store.transaction() as uow:
            action = uow.get_action_by_id(principal.tenant_id, action_id)
            if action is None:
                raise NotFoundError()
            _scope_case(principal, action.case_id)
            if action.status != "PROPOSED":
                raise ConflictError("Only PROPOSED actions accept decisions")
            if action.action_digest != action_digest_value:
                raise ConflictError("Approval digest mismatch", code="DIGEST_MISMATCH")
            if action.case_revision != case_revision:
                raise ConflictError("Approval case_revision mismatch", code="REVISION_MISMATCH")
            if action.policy_version != policy_version:
                raise ConflictError("Approval policy_version mismatch", code="POLICY_MISMATCH")
            existing = uow.get_approval_for_action(principal.tenant_id, action_id)
            if existing is not None:
                if (
                    existing.decision == decision
                    and existing.action_digest == action_digest_value
                    and existing.case_revision == case_revision
                    and existing.policy_version == policy_version
                    and existing.expires_at == expires_at
                ):
                    return existing
                raise ConflictError("Action already has a conflicting approval")
            approval = Approval(
                approval_id=self._ids.new_id("approval"),
                action_digest=action_digest_value,
                case_revision=case_revision,
                policy_version=policy_version,
                decision=decision,  # type: ignore[arg-type]
                reviewer_id=principal.principal_id,
                expires_at=expires_at,
            )
            uow.insert_approval(
                tenant_id=principal.tenant_id,
                action_id=action_id,
                approval=approval,
                created_at=_iso(now),
            )
            uow.insert_audit(
                tenant_id=principal.tenant_id,
                action_id=action_id,
                event_type="DECISION",
                actor_id=principal.principal_id,
                detail={"decision": decision, "approval_id": approval.approval_id},
                occurred_at=_iso(now),
            )
            return approval

    def reserve(
        self,
        principal: Principal,
        *,
        operation_key: str,
        payload: dict[str, Any],
        digest: str,
        approval_id: str,
        order_reference: str | None = None,
    ) -> tuple[ActionRecord, bool]:
        """Prepare eligibility outside TX; reserve/action/outbox/audit atomic inside TX."""
        _require_roles(principal, "workflow")
        normalized = canonical_refund_payload(payload)
        expected = action_digest(normalized)
        if digest != expected:
            raise ValidationError("action_digest does not match payload", code="DIGEST_MISMATCH")
        _scope_case(principal, normalized["case_id"])

        # Network/evidence BEFORE the reservation transaction.
        evidence_items = list(
            self._evidence.collect(
                principal=principal,
                case_id=normalized["case_id"],
                case_revision=normalized["case_revision"],
                order_reference=order_reference or f"ORDER-{normalized['transaction_ref']}",
            )
        )
        snapshot = self._build_eligibility(principal, normalized, evidence_items)
        # Policy check also outside reservation TX (peer may be remote).
        self._policy.evaluate(
            principal=principal,
            payload=normalized,
            evidence=evidence_items,
        )

        now = self._clock.now()
        now_s = _iso(now)
        with self._network.begin_guard():
            with self._store.transaction() as uow:
                self._network.assert_idle()
                existing = uow.get_action_by_operation_key(principal.tenant_id, operation_key)
                if existing is not None and existing.status != "PROPOSED":
                    if existing.action_digest != expected or existing.payload != normalized:
                        raise ConflictError(
                            "Key already used with a different payload",
                            code="IDEMPOTENCY_CONFLICT",
                        )
                    return uow.to_record(existing), False
                if existing is None:
                    raise ConflictError(
                        "Reservation requires an existing approved proposal",
                        code="PROPOSAL_REQUIRED",
                    )
                if existing.action_digest != expected or existing.payload != normalized:
                    raise ConflictError(
                        "Key already used with a different payload",
                        code="IDEMPOTENCY_CONFLICT",
                    )
                if existing.case_id != normalized["case_id"]:
                    raise ConflictError("Reservation case mismatch")
                if existing.case_revision != normalized["case_revision"]:
                    raise ConflictError("Reservation case_revision mismatch")

                approval = uow.get_approval(principal.tenant_id, approval_id)
                if approval is None:
                    raise ConflictError("Unknown approval_id", code="APPROVAL_REQUIRED")
                if approval.decision != "APPROVE":
                    raise ConflictError("Approval is not APPROVE", code="APPROVAL_REJECTED")
                if approval.action_digest != expected:
                    raise ConflictError("Approval digest mismatch", code="DIGEST_MISMATCH")
                if approval.case_revision != normalized["case_revision"]:
                    raise ConflictError("Approval revision mismatch", code="REVISION_MISMATCH")
                if approval.policy_version != normalized["policy_version"]:
                    raise ConflictError("Approval policy mismatch", code="POLICY_MISMATCH")
                if approval.expires_at <= now_s:
                    raise ConflictError("Approval expired", code="APPROVAL_EXPIRED")
                action_approval = uow.get_approval_for_action(
                    principal.tenant_id, existing.action_id
                )
                if action_approval is None or action_approval.approval_id != approval_id:
                    raise ConflictError("Approval does not bind this action")

                # Lock payment first so eligibility version bumps serialize under concurrency.
                uow.upsert_payment(
                    tenant_id=principal.tenant_id,
                    transaction_ref=normalized["transaction_ref"],
                    merchant_ref=snapshot.case_id,
                    captured_minor=snapshot.captured_minor
                    - snapshot.external_refunded_minor
                    - snapshot.external_pending_minor,
                    currency=snapshot.currency,
                )
                balance = uow.lock_payment(principal.tenant_id, normalized["transaction_ref"])
                if balance is None:
                    raise ConflictError("Payment reservation row missing")

                existing_elig = uow.get_eligibility(
                    principal.tenant_id, normalized["transaction_ref"]
                )
                next_version = existing_elig.version + 1 if existing_elig is not None else 1
                versioned = replace(snapshot, version=next_version)
                uow.upsert_eligibility(versioned)
                locked_elig = uow.get_eligibility(
                    principal.tenant_id, normalized["transaction_ref"]
                )
                if locked_elig is None or locked_elig.expires_at <= now_s:
                    raise ConflictError("Eligibility snapshot expired", code="ELIGIBILITY_EXPIRED")
                if locked_elig.payment_status != "CAPTURED":
                    raise ConflictError("Payment not eligible for refund")
                # DB bumps version atomically on conflict; accept the stored row.
                if locked_elig.version < next_version:
                    raise ConflictError("Eligibility snapshot superseded")

                new_balance = apply_reserve(balance, normalized["amount_minor"])
                uow.write_payment_balance(
                    principal.tenant_id, normalized["transaction_ref"], new_balance
                )

                reserved = StoredAction(
                    tenant_id=existing.tenant_id,
                    action_id=existing.action_id,
                    operation_key=existing.operation_key,
                    provider_ref=existing.provider_ref,
                    payload=existing.payload,
                    action_digest=existing.action_digest,
                    status="RESERVED",
                    amount_minor=existing.amount_minor,
                    currency=existing.currency,
                    transaction_ref=existing.transaction_ref,
                    case_id=existing.case_id,
                    case_revision=existing.case_revision,
                    policy_version=existing.policy_version,
                    approval_id=approval_id,
                    lease_id=None,
                    lease_expires_at=None,
                    created_at=existing.created_at,
                    updated_at=now_s,
                )
                uow.update_action(reserved)
                uow.insert_outbox(
                    tenant_id=principal.tenant_id,
                    action_id=reserved.action_id,
                    available_at=now_s,
                    payload={
                        "provider_ref": reserved.provider_ref,
                        "action_digest": reserved.action_digest,
                        "payload": reserved.payload,
                        "provider_capabilities": self._provider_capabilities,
                    },
                )
                uow.insert_audit(
                    tenant_id=principal.tenant_id,
                    action_id=reserved.action_id,
                    event_type="RESERVED",
                    actor_id=principal.principal_id,
                    detail={
                        "amount_minor": normalized["amount_minor"],
                        "approval_id": approval_id,
                        "remaining_minor": new_balance.remaining(),
                    },
                    occurred_at=now_s,
                )
                self._network.assert_idle()
                return uow.to_record(reserved), True

    def claim(self, principal: Principal, *, limit: int) -> ClaimResult:
        _require_roles(principal, "dispatcher")
        if not isinstance(limit, int) or limit < 1 or limit > 100:
            raise ValidationError("limit must be an integer from 1 to 100")
        now = self._clock.now()
        lease_expires = _iso(now + timedelta(seconds=self._lease_seconds))
        with self._store.transaction() as uow:
            claimed = uow.claim_outbox(
                tenant_id=principal.tenant_id,
                limit=limit,
                lease_expires_at=lease_expires,
                now=_iso(now),
                new_lease_id=lambda: self._ids.new_id("lease"),
            )
            commands = []
            for command in claimed:
                action = uow.get_action_by_id(principal.tenant_id, command.action_id)
                if action is None:
                    continue
                if action.status not in {"RESERVED", "DISPATCHING"}:
                    # Dispatch already progressed; finish outbox and skip rewrite.
                    uow.mark_outbox_done(tenant_id=principal.tenant_id, action_id=command.action_id)
                    continue
                assert_transition(action.status, "DISPATCHING", roles=principal.roles)  # type: ignore[arg-type]
                updated = replace(
                    action,
                    status="DISPATCHING",
                    lease_id=command.lease_id,
                    lease_expires_at=command.lease_expires_at,
                    updated_at=_iso(now),
                )
                uow.update_action(updated)
                uow.insert_audit(
                    tenant_id=principal.tenant_id,
                    action_id=command.action_id,
                    event_type="CLAIMED",
                    actor_id=principal.principal_id,
                    detail={"lease_id": command.lease_id},
                    occurred_at=_iso(now),
                )
                commands.append(command)
            return ClaimResult(commands=tuple(commands))

    def get(self, principal: Principal, *, action_id: str) -> ActionRecord:
        _require_roles(principal, "workflow", "dispatcher", "verifier", "operator", "supervisor")
        with self._store.transaction() as uow:
            action = uow.get_action_by_id(principal.tenant_id, action_id)
            if action is None:
                raise NotFoundError()
            _scope_case(principal, action.case_id)
            return uow.to_record(action)

    def outcome(
        self,
        principal: Principal,
        *,
        action_id: str,
        event_key: str,
        status: str,
        evidence: list[dict[str, Any]],
        reason_code: str,
        lease_id: str | None = None,
    ) -> ActionRecord:
        target = validate_outcome_status(status)
        now_s = _iso(self._clock.now())
        with self._store.transaction() as uow:
            action = uow.get_action_by_id(principal.tenant_id, action_id)
            if action is None:
                raise NotFoundError()
            _scope_case(principal, action.case_id)
            inserted = uow.record_outcome_event(
                tenant_id=principal.tenant_id,
                action_id=action_id,
                event_key=event_key,
                status=target,
                reason_code=reason_code,
                evidence_ids=[item.get("evidence_id", "") for item in evidence],
                occurred_at=now_s,
            )
            if not inserted:
                return uow.to_record(action)

            assert_transition(action.status, target, roles=principal.roles)  # type: ignore[arg-type]
            if principal.has_role("dispatcher") and target in {
                "PENDING",
                "OUTCOME_UNKNOWN",
                "ESCALATED",
            }:
                if lease_id is None or lease_id != action.lease_id:
                    raise ConflictError("lease_id mismatch", code="LEASE_MISMATCH")
            required_kinds = require_evidence_kinds(target)
            if required_kinds:
                self._assert_outcome_evidence(evidence, required_kinds, action)

            previous = action.status
            balance = uow.lock_payment(principal.tenant_id, action.transaction_ref)
            if balance is None and target != "ESCALATED":
                raise ConflictError("Payment balance missing")
            if balance is not None:
                balance = self._apply_balance_transition(
                    balance, action.amount_minor, previous, target
                )
                uow.write_payment_balance(principal.tenant_id, action.transaction_ref, balance)

            updated = replace(action, status=target, updated_at=now_s)
            uow.update_action(updated)
            if target in {
                "PENDING",
                "PROVIDER_CONFIRMED",
                "FAILED_FINAL",
                "CREDIT_CONFIRMED",
                "OUTCOME_UNKNOWN",
                "ESCALATED",
            }:
                uow.mark_outbox_done(tenant_id=principal.tenant_id, action_id=action_id)
            uow.insert_audit(
                tenant_id=principal.tenant_id,
                action_id=action_id,
                event_type="OUTCOME",
                actor_id=principal.principal_id,
                detail={
                    "from": previous,
                    "to": target,
                    "event_key": event_key,
                    "reason_code": reason_code,
                },
                occurred_at=now_s,
            )
            return uow.to_record(updated)

    def _apply_balance_transition(self, balance, amount, previous, target):
        # Escalation retains allocations.
        if target == "ESCALATED":
            return balance
        if target == "PENDING" and previous in {"DISPATCHING", "OUTCOME_UNKNOWN", "ESCALATED"}:
            if previous in PENDING_BALANCE_STATES:
                return balance
            # From reserved-side states move reserved → pending once.
            if previous in {"DISPATCHING", "OUTCOME_UNKNOWN", "ESCALATED", "RESERVED"}:
                # DISPATCHING/OUTCOME_UNKNOWN/ESCALATED still hold reserved.
                return reserved_to_pending(balance, amount)
        if target == "OUTCOME_UNKNOWN":
            return balance
        if target in COMPLETED_BALANCE_STATES:
            from_pending = previous in PENDING_BALANCE_STATES or previous == "ESCALATED"
            # If still reserved (e.g. OUTCOME_UNKNOWN → PROVIDER_CONFIRMED), take from reserved.
            if previous in {"OUTCOME_UNKNOWN", "DISPATCHING", "RESERVED"} or (
                previous == "ESCALATED" and balance.reserved_minor >= amount
            ):
                from_pending = False
            if previous == "PENDING" or (
                previous == "ESCALATED" and balance.pending_minor >= amount
            ):
                from_pending = True
            if target == "CREDIT_CONFIRMED":
                # Already counted as completed at PROVIDER_CONFIRMED.
                return balance
            return reserved_or_pending_to_refunded(balance, amount, from_pending=from_pending)
        if target == "FAILED_FINAL":
            from_pending = previous == "PENDING" or (
                previous == "ESCALATED" and balance.pending_minor >= amount
            )
            return release_allocation(balance, amount, from_pending=from_pending)
        return balance

    def _assert_outcome_evidence(
        self, evidence: list[dict[str, Any]], required_kinds: frozenset[str], action: StoredAction
    ) -> None:
        if not evidence:
            raise ValidationError("Verified evidence required for this transition")
        kinds: set[str] = set()
        for item in evidence:
            if item.get("verification_status") != "VERIFIED":
                raise ConflictError("Evidence not verified")
            facts = item.get("facts") or {}
            kind = facts.get("kind")
            if kind:
                kinds.add(kind)
            expires_at = item.get("expires_at")
            if not expires_at or expires_at <= _iso(self._clock.now()):
                raise ConflictError("Evidence expired")
            if item.get("case_id") != action.case_id:
                raise ConflictError("Evidence case mismatch")
            if kind == "REFUND" and "REFUND" in required_kinds:
                self._assert_refund_evidence_binds(facts.get("refund") or {}, action)
            elif kind == "CREDIT" and "CREDIT" in required_kinds:
                self._assert_credit_evidence_binds(facts.get("credit") or {}, action)
        if not required_kinds.issubset(kinds):
            raise ConflictError("Evidence kind mismatch for transition")

    def _assert_refund_evidence_binds(self, refund: dict[str, Any], action: StoredAction) -> None:
        if (
            refund.get("amount_minor") != action.amount_minor
            or refund.get("currency") != action.currency
            or refund.get("provider_ref") != action.provider_ref
            or refund.get("transaction_ref") != action.transaction_ref
        ):
            raise ConflictError("Evidence does not match action", code="EVIDENCE_MISMATCH")

    def _assert_credit_evidence_binds(self, credit: dict[str, Any], action: StoredAction) -> None:
        if credit.get("provider_ref") != action.provider_ref:
            raise ConflictError("Evidence does not match action", code="EVIDENCE_MISMATCH")
        if "amount_minor" in credit and credit.get("amount_minor") != action.amount_minor:
            raise ConflictError("Evidence does not match action", code="EVIDENCE_MISMATCH")

    def _build_eligibility(
        self,
        principal: Principal,
        payload: dict[str, Any],
        evidence_items: list[EvidenceItem],
    ) -> EligibilitySnapshot:
        now_s = _iso(self._clock.now())
        payment = None
        external_refunded = 0
        external_pending = 0
        for item in evidence_items:
            if item.verification_status != "VERIFIED":
                continue
            if item.expires_at <= now_s:
                continue
            if item.case_id != payload["case_id"]:
                continue
            facts = item.facts
            kind = facts.get("kind")
            if kind == "PAYMENT":
                payment_obj = facts.get("payment") or {}
                if payment_obj.get("transaction_ref") == payload["transaction_ref"]:
                    payment = (item, payment_obj)
            elif kind == "REFUND":
                refund = facts.get("refund") or {}
                if refund.get("transaction_ref") == payload["transaction_ref"]:
                    status = refund.get("status")
                    amount = int(refund.get("amount_minor") or 0)
                    if status == "PROVIDER_CONFIRMED":
                        external_refunded += amount
                    elif status == "PENDING":
                        external_pending += amount
        if payment is None:
            raise ConflictError("No fresh verified payment evidence", code="NEED_EVIDENCE")
        item, payment_obj = payment
        if payment_obj.get("status") != "CAPTURED":
            raise ConflictError("Payment not captured")
        if payment_obj.get("currency") != payload["currency"]:
            raise ConflictError("Currency mismatch")
        payment_subject = str(payment_obj.get("subject_ref") or item.subject_ref)
        # Empty subject_refs allowed for service principals; non-empty must contain payment subject.
        if principal.subject_refs and payment_subject not in principal.subject_refs:
            raise ForbiddenError("Subject outside principal scope")
        captured = int(payment_obj["amount_minor"])
        return EligibilitySnapshot(
            tenant_id=principal.tenant_id,
            transaction_ref=payload["transaction_ref"],
            case_id=payload["case_id"],
            subject_ref=payment_subject,
            captured_minor=captured,
            currency=payload["currency"],
            payment_status="CAPTURED",
            observed_at=item.observed_at,
            expires_at=item.expires_at,
            evidence_digest=item.digest,
            external_refunded_minor=external_refunded,
            external_pending_minor=external_pending,
            version=1,
        )
