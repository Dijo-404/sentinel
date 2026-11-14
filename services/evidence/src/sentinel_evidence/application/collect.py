"""Collect and list evidence use cases."""

from __future__ import annotations

from ..domain.digest import sha256_hex
from ..domain.order_reference import OrderReferenceError, provider_order_id
from ..domain.reconcile import apply_status, classify_verification, parse_rfc3339, reconcile_codes
from ..domain.types import (
    CONTRACT_VERSION,
    CollectRequest,
    Evidence,
    EvidenceBundle,
    Payment,
    Principal,
    ProviderSnapshot,
)
from .errors import NotFoundError, UnauthorizedError, ValidationError
from .ports import Clock, EvidenceStore, PaymentProviderPort

COLLECT_ROLES = frozenset({"workflow", "verifier"})
LIST_ROLES = frozenset({"workflow", "verifier", "operator", "supervisor"})


def _require_roles(principal: Principal, allowed: frozenset[str]) -> None:
    if not allowed.intersection(principal.roles):
        raise UnauthorizedError("Principal lacks required role")


def _require_case_scope(principal: Principal, case_id: str) -> None:
    if not principal.allows_case(case_id):
        raise UnauthorizedError("Case is outside authenticated scope")


def _require_subject_scope(principal: Principal, subject_ref: str) -> None:
    if subject_ref not in principal.subject_refs:
        raise UnauthorizedError("Subject is outside authenticated scope")


def _validate_collect(request: CollectRequest) -> None:
    if not request.case_id or not isinstance(request.case_id, str):
        raise ValidationError("case_id is required")
    if not isinstance(request.case_revision, int) or request.case_revision < 1:
        raise ValidationError("case_revision must be a positive integer")
    if not request.order_reference or not isinstance(request.order_reference, str):
        raise ValidationError("order_reference is required")


def _build_evidence(case_id: str, snapshot: ProviderSnapshot) -> tuple[Evidence, ...]:
    items: list[Evidence] = []
    for index, (payload, payment) in enumerate(snapshot.payment_items):
        digest = sha256_hex(payload)
        items.append(
            Evidence(
                evidence_id=f"evidence-payment-{payment.transaction_ref}-{index}",
                case_id=case_id,
                source="payment-provider.v1/transactions",
                subject_ref=payment.subject_ref,
                observed_at=snapshot.observed_at,
                expires_at=snapshot.expires_at,
                digest=digest,
                verification_status="VERIFIED",
                facts={
                    "kind": "PAYMENT",
                    "payment": {
                        "transaction_ref": payment.transaction_ref,
                        "order_reference": payment.order_reference,
                        "subject_ref": payment.subject_ref,
                        "status": payment.status,
                        "amount_minor": payment.amount_minor,
                        "currency": payment.currency,
                    },
                },
                payload_utf8=payload,
            )
        )

    order_payload = snapshot.order_payload
    order = snapshot.order
    items.append(
        Evidence(
            evidence_id="evidence-order",
            case_id=case_id,
            source="payment-provider.v1/orders",
            subject_ref=order.subject_ref,
            observed_at=snapshot.observed_at,
            expires_at=snapshot.expires_at,
            digest=sha256_hex(order_payload),
            verification_status="VERIFIED",
            facts={
                "kind": "ORDER",
                "order": {
                    "order_reference": order.order_reference,
                    "subject_ref": order.subject_ref,
                    "fulfilled_order_count": order.fulfilled_order_count,
                    "merchant_confirmed_duplicate": order.merchant_confirmed_duplicate,
                    "paid": order.paid,
                },
            },
            payload_utf8=order_payload,
        )
    )

    for payload, refund in snapshot.refund_items:
        subject = order.subject_ref
        for payment in snapshot.payments:
            if payment.transaction_ref == refund.transaction_ref:
                subject = payment.subject_ref
                break
        items.append(
            Evidence(
                evidence_id=f"evidence-refund-{refund.provider_ref}",
                case_id=case_id,
                source="payment-provider.v1/refunds",
                subject_ref=subject,
                observed_at=snapshot.observed_at,
                expires_at=snapshot.expires_at,
                digest=sha256_hex(payload),
                verification_status="VERIFIED",
                facts={
                    "kind": "REFUND",
                    "refund": {
                        "action_id": refund.action_id,
                        "provider_ref": refund.provider_ref,
                        "transaction_ref": refund.transaction_ref,
                        "amount_minor": refund.amount_minor,
                        "currency": refund.currency,
                        "status": refund.status,
                    },
                },
                payload_utf8=payload,
            )
        )
    return tuple(items)


def _detect_conflicts(snapshot: ProviderSnapshot) -> bool:
    by_ref: dict[str, Payment] = {}
    for payment in snapshot.payments:
        prior = by_ref.get(payment.transaction_ref)
        if prior is not None and (
            prior.amount_minor != payment.amount_minor
            or prior.status != payment.status
            or prior.subject_ref != payment.subject_ref
        ):
            return True
        by_ref[payment.transaction_ref] = payment
    if any(p.subject_ref != snapshot.order.subject_ref for p in snapshot.payments):
        return True
    return False


class CollectEvidence:
    def __init__(self, provider: PaymentProviderPort, store: EvidenceStore, clock: Clock):
        self._provider = provider
        self._store = store
        self._clock = clock

    def __call__(self, principal: Principal, request: CollectRequest) -> EvidenceBundle:
        _require_roles(principal, COLLECT_ROLES)
        _require_case_scope(principal, request.case_id)
        _validate_collect(request)

        # Authorized case identity stays on the request/store; provider keys are bare.
        try:
            provider_key = provider_order_id(request.order_reference)
        except OrderReferenceError as exc:
            raise ValidationError(str(exc)) from exc
        snapshot = self._provider.fetch_snapshot(
            order_reference=provider_key,
            principal=principal,
        )
        _require_subject_scope(principal, snapshot.order.subject_ref)
        for payment in snapshot.payments:
            _require_subject_scope(principal, payment.subject_ref)

        now = self._clock.now()
        stale = parse_rfc3339(snapshot.expires_at) <= now
        conflicting = _detect_conflicts(snapshot)
        status = classify_verification(
            expires_at=snapshot.expires_at,
            now=now,
            conflicting=conflicting,
        )
        evidence = apply_status(_build_evidence(request.case_id, snapshot), status)
        codes = reconcile_codes(
            payments=snapshot.payments,
            order=snapshot.order,
            refunds=snapshot.refunds,
            stale=stale,
            conflicting=conflicting,
        )
        bundle = EvidenceBundle(
            contract_version=CONTRACT_VERSION,
            case_id=request.case_id,
            evidence=evidence,
            reconciliation_codes=codes,
        )
        return self._store.save_bundle(principal=principal, request=request, bundle=bundle)


class ListEvidence:
    def __init__(self, store: EvidenceStore):
        self._store = store

    def __call__(self, principal: Principal, case_id: str) -> EvidenceBundle:
        _require_roles(principal, LIST_ROLES)
        _require_case_scope(principal, case_id)
        if not case_id:
            raise ValidationError("case_id is required")
        bundle = self._store.get_bundle(principal=principal, case_id=case_id)
        if bundle is None:
            raise NotFoundError("No evidence collected for case")
        return bundle
