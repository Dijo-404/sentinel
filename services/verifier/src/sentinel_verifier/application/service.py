"""Verifier use cases: webhook inbox, rechecks, and closure assessment."""

from __future__ import annotations

import hashlib
import json
from datetime import timedelta
from typing import Any

from sentinel_verifier import CONTRACT_VERSION
from sentinel_verifier.application.ports import (
    CaseApiPort,
    Clock,
    EvidencePort,
    IdGenerator,
    LedgerPort,
    ProviderPort,
    VerifierStore,
)
from sentinel_verifier.domain.assessment import classify_outcomes
from sentinel_verifier.domain.errors import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from sentinel_verifier.domain.signature import verify_signature
from sentinel_verifier.domain.types import (
    Ack,
    InboxRecord,
    OutcomeRequest,
    Principal,
    ProviderBinding,
    RecheckJob,
    VerificationRequest,
    VerificationResult,
    WebhookEvent,
)

PROVIDER_NAME = "simulator"
ASSESSMENT_TTL = timedelta(hours=1)
RECHECK_LEASE = timedelta(minutes=5)
DEFAULT_MAX_AGE = timedelta(hours=24)


class VerifierService:
    def __init__(
        self,
        *,
        store: VerifierStore,
        clock: Clock,
        ids: IdGenerator,
        provider: ProviderPort,
        ledger: LedgerPort,
        evidence: EvidencePort,
        case_api: CaseApiPort,
        webhook_hmac_key: str,
        merchant_map: dict[str, str],
        max_event_age: timedelta | None = DEFAULT_MAX_AGE,
        enforce_event_age: bool = True,
    ) -> None:
        self._store = store
        self._clock = clock
        self._ids = ids
        self._provider = provider
        self._ledger = ledger
        self._evidence = evidence
        self._case_api = case_api
        self._webhook_hmac_key = webhook_hmac_key
        self._merchant_map = merchant_map
        self._max_event_age = max_event_age
        self._enforce_event_age = enforce_event_age

    def ingest_webhook(self, *, raw_body: bytes, signature: str | None) -> dict[str, bool]:
        if not signature or not verify_signature(
            raw_body, key=self._webhook_hmac_key, provided=signature
        ):
            raise UnauthorizedError("Invalid provider signature")
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValidationError("Malformed webhook body") from exc
        event = self._parse_webhook(payload)
        mapped_tenant = self._merchant_map.get(event.merchant_ref)
        if mapped_tenant is None or mapped_tenant != event.tenant_id:
            raise ForbiddenError("Merchant tenant mapping rejected")
        if self._enforce_event_age and self._max_event_age is not None:
            occurred = _parse_iso(event.occurred_at)
            age = self._clock.now() - occurred
            if age > self._max_event_age or age < -timedelta(minutes=5):
                raise ValidationError("Webhook failed replay/age policy", code="REPLAY_REJECTED")

        now = self._clock.now().isoformat().replace("+00:00", "Z")
        record = InboxRecord(
            tenant_id=event.tenant_id,
            event_id=event.event_id,
            provider=PROVIDER_NAME,
            provider_ref=event.provider_ref,
            event_type=event.type,
            merchant_ref=event.merchant_ref,
            occurred_at=event.occurred_at,
            payload_json=raw_body.decode("utf-8"),
            signature_hex=signature.strip().lower(),
            received_at=now,
            processed_at=None,
            process_status="ACCEPTED",
            reason_code=None,
        )
        stored = self._store.insert_inbox(record)
        if not stored.duplicate:
            self._process_provider_ref(
                tenant_id=event.tenant_id,
                provider_ref=event.provider_ref,
                source_event_id=event.event_id,
            )
            self._store.mark_inbox_processed(
                event.tenant_id,
                event.event_id,
                process_status="PROCESSED",
                reason_code="RECONCILED",
                processed_at=self._clock.now().isoformat().replace("+00:00", "Z"),
            )
        return {"accepted": True}

    def schedule_recheck(
        self,
        principal: Principal,
        request: VerificationRequest,
        *,
        idempotency_key: str,
    ) -> Ack:
        self._require_roles(principal, "workflow", "verifier")
        self._require_case_scope(principal, request.case_id)
        if not idempotency_key:
            raise ValidationError("Idempotency-Key required")
        digest = _request_digest(request)
        existing = self._store.get_recheck_by_idempotency(principal.tenant_id, idempotency_key)
        if existing is not None:
            if existing.request_digest != digest:
                raise ConflictError(
                    "Key already used with a different payload",
                    code="IDEMPOTENCY_CONFLICT",
                )
            return Ack(CONTRACT_VERSION, existing.job_id)

        now = self._clock.now()
        job_id = self._ids.new_id("job")
        job = RecheckJob(
            tenant_id=principal.tenant_id,
            job_id=job_id,
            idempotency_key=idempotency_key,
            case_id=request.case_id,
            case_revision=request.case_revision,
            action_id=request.action_id,
            provider_ref=request.provider_ref,
            request_digest=digest,
            available_at=now.isoformat().replace("+00:00", "Z"),
            lease_expires_at=(now + RECHECK_LEASE).isoformat().replace("+00:00", "Z"),
            attempts=0,
            status="SCHEDULED",
            created_at=now.isoformat().replace("+00:00", "Z"),
            updated_at=now.isoformat().replace("+00:00", "Z"),
        )
        self._store.save_recheck(job)
        self._store.save_binding(
            ProviderBinding(
                tenant_id=principal.tenant_id,
                provider_ref=request.provider_ref,
                action_id=request.action_id,
                case_id=request.case_id,
                case_revision=request.case_revision,
                updated_at=now.isoformat().replace("+00:00", "Z"),
            )
        )
        self._process_provider_ref(
            tenant_id=principal.tenant_id,
            provider_ref=request.provider_ref,
            source_event_id=job_id,
        )
        return Ack(CONTRACT_VERSION, job_id)

    def create_assessment(
        self, principal: Principal, request: VerificationRequest
    ) -> VerificationResult:
        self._require_roles(principal, "workflow")
        self._require_case_scope(principal, request.case_id)
        now = self._clock.now()
        self._store.save_binding(
            ProviderBinding(
                tenant_id=principal.tenant_id,
                provider_ref=request.provider_ref,
                action_id=request.action_id,
                case_id=request.case_id,
                case_revision=request.case_revision,
                updated_at=now.isoformat().replace("+00:00", "Z"),
            )
        )
        result = self._assess(principal.tenant_id, request)
        self._store.save_assessment(result, tenant_id=principal.tenant_id)
        if result.status == "VERIFIED" and "CREDIT_CONFIRMED" in result.reason_codes:
            self._announce_case_result(principal.tenant_id, result)
        return result

    def get_assessment(self, principal: Principal, assessment_id: str) -> VerificationResult:
        self._require_roles(principal, "workflow", "verifier")
        result = self._store.get_assessment(principal.tenant_id, assessment_id)
        if result is None:
            raise NotFoundError("Assessment not found")
        self._require_case_scope(principal, result.case_id)
        return result

    def _assess(self, tenant_id: str, request: VerificationRequest) -> VerificationResult:
        action = self._ledger.get_action(request.action_id)
        if action.get("provider_ref") != request.provider_ref:
            raise ValidationError("provider_ref does not match action")
        refund = self._provider.get_refund(request.provider_ref)
        credit = self._provider.get_credit(request.provider_ref)
        evidence_bundle = self._evidence.get_case_evidence(request.case_id)
        evidence = list(evidence_bundle.get("evidence") or [])
        evidence.extend(
            self._synthetic_provider_evidence(
                request=request,
                refund=refund,
                credit=credit,
            )
        )
        status, reasons, ledger_targets = classify_outcomes(
            action_status=str(action.get("status") or ""),
            refund=refund,
            credit=credit,
            evidence=evidence,
        )
        for ledger_target in ledger_targets:
            self._post_ledger_outcome(
                action_id=request.action_id,
                provider_ref=request.provider_ref,
                target=ledger_target,
                evidence=evidence,
                source="assessment",
            )
        now = self._clock.now()
        return VerificationResult(
            assessment_id=self._ids.new_id("assessment"),
            case_id=request.case_id,
            case_revision=request.case_revision,
            action_id=request.action_id,
            assessed_at=now.isoformat().replace("+00:00", "Z"),
            expires_at=(now + ASSESSMENT_TTL).isoformat().replace("+00:00", "Z"),
            status=status,
            evidence=tuple(evidence),
            reason_codes=reasons,
        )

    def _process_provider_ref(
        self, *, tenant_id: str, provider_ref: str, source_event_id: str
    ) -> None:
        binding = self._store.get_binding(tenant_id, provider_ref)
        if binding is None:
            return
        action = self._ledger.get_action(binding.action_id)
        refund = self._provider.get_refund(provider_ref)
        credit = self._provider.get_credit(provider_ref)
        evidence = self._synthetic_provider_evidence(
            request=VerificationRequest(
                case_id=binding.case_id,
                case_revision=binding.case_revision,
                action_id=binding.action_id,
                provider_ref=provider_ref,
            ),
            refund=refund,
            credit=credit,
        )
        _status, _reasons, ledger_targets = classify_outcomes(
            action_status=str(action.get("status") or ""),
            refund=refund,
            credit=credit,
            evidence=evidence,
        )
        for ledger_target in ledger_targets:
            self._post_ledger_outcome(
                action_id=binding.action_id,
                provider_ref=provider_ref,
                target=ledger_target,
                evidence=evidence,
                source=source_event_id,
            )

    def _post_ledger_outcome(
        self,
        *,
        action_id: str,
        provider_ref: str,
        target: str,
        evidence: list[dict[str, Any]],
        source: str,
    ) -> None:
        event_key = f"verifier-{provider_ref}-{target}-{source}"
        self._ledger.report_outcome(
            action_id,
            OutcomeRequest(
                event_key=event_key,
                status=target,  # type: ignore[arg-type]
                evidence=tuple(evidence),
                reason_code=target,
            ),
        )

    def _announce_case_result(self, tenant_id: str, result: VerificationResult) -> None:
        del tenant_id
        self._case_api.submit_result(
            result.case_id,
            {
                "event_key": f"verified-{result.assessment_id}",
                "expected_revision": result.case_revision,
                "status": "VERIFIED_RESOLVED",
                "evidence_ids": [
                    e.get("evidence_id") for e in result.evidence if e.get("evidence_id")
                ],
                "action_id": result.action_id,
                "assessment_id": result.assessment_id,
                "reason_code": "CREDIT_CONFIRMED",
            },
        )

    def _synthetic_provider_evidence(
        self,
        *,
        request: VerificationRequest,
        refund: Any,
        credit: Any,
    ) -> list[dict[str, Any]]:
        now = self._clock.now().isoformat().replace("+00:00", "Z")
        items: list[dict[str, Any]] = []
        if refund is not None:
            items.append(
                {
                    "evidence_id": f"evidence-refund-{refund.provider_ref}",
                    "case_id": request.case_id,
                    "source": "payment-provider.v1",
                    "subject_ref": "subject-demo-1",
                    "observed_at": now,
                    "expires_at": (self._clock.now() + ASSESSMENT_TTL)
                    .isoformat()
                    .replace("+00:00", "Z"),
                    "digest": hashlib.sha256(
                        json.dumps(
                            {
                                "provider_ref": refund.provider_ref,
                                "status": refund.status,
                            },
                            sort_keys=True,
                        ).encode()
                    ).hexdigest(),
                    "verification_status": "VERIFIED",
                    "facts": {
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
                }
            )
        if credit is not None:
            items.append(
                {
                    "evidence_id": f"evidence-credit-{credit.provider_ref}",
                    "case_id": request.case_id,
                    "source": "payment-provider.v1",
                    "subject_ref": "subject-demo-1",
                    "observed_at": credit.observed_at,
                    "expires_at": (self._clock.now() + ASSESSMENT_TTL)
                    .isoformat()
                    .replace("+00:00", "Z"),
                    "digest": hashlib.sha256(
                        json.dumps(
                            {
                                "provider_ref": credit.provider_ref,
                                "confirmed": credit.confirmed,
                            },
                            sort_keys=True,
                        ).encode()
                    ).hexdigest(),
                    "verification_status": "VERIFIED" if credit.confirmed else "UNVERIFIED",
                    "facts": {
                        "kind": "CREDIT",
                        "credit": {
                            "provider_ref": credit.provider_ref,
                            "confirmed": credit.confirmed,
                            "observed_at": credit.observed_at,
                        },
                    },
                }
            )
        return items

    def _parse_webhook(self, payload: dict[str, Any]) -> WebhookEvent:
        required = (
            "event_id",
            "tenant_id",
            "merchant_ref",
            "provider_ref",
            "type",
            "occurred_at",
        )
        missing = [key for key in required if key not in payload]
        if missing:
            raise ValidationError(f"Missing webhook fields: {', '.join(missing)}")
        event_type = payload["type"]
        if event_type not in {"REFUND_STATUS", "CREDIT_STATUS"}:
            raise ValidationError("Unsupported webhook type")
        return WebhookEvent(
            event_id=str(payload["event_id"]),
            tenant_id=str(payload["tenant_id"]),
            merchant_ref=str(payload["merchant_ref"]),
            provider_ref=str(payload["provider_ref"]),
            type=event_type,
            occurred_at=str(payload["occurred_at"]),
        )

    @staticmethod
    def _require_roles(principal: Principal, *roles: str) -> None:
        if not principal.has_role(*roles):
            raise ForbiddenError("Role not permitted for this route")

    @staticmethod
    def _require_case_scope(principal: Principal, case_id: str) -> None:
        if not principal.allows_case(case_id):
            raise ForbiddenError("Case out of principal scope")


def _request_digest(request: VerificationRequest) -> str:
    canonical = json.dumps(request.as_dict(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _parse_iso(value: str):
    from datetime import UTC, datetime

    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed
