"""In-process fixture peers used only when mode=fixture is explicit."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from sentinel_api.adapters.peers.errors import malformed, unauthorized, unavailable
from sentinel_api.domain.types import (
    CONTRACT_VERSION,
    Approval,
    DecisionRequest,
    EvidenceBundle,
    VerificationResult,
    WorkflowRequest,
)

PeerBehavior = Literal["valid", "unavailable", "malformed", "unauthorized_or_out_of_scope"]


@dataclass
class FixtureWorkflowClient:
    behavior: PeerBehavior = "valid"
    calls: list[WorkflowRequest] = field(default_factory=list)

    def start_run(self, request: WorkflowRequest, *, authorization: str) -> None:
        _ = authorization
        if self.behavior == "unavailable":
            raise unavailable("workflow")
        if self.behavior == "malformed":
            raise malformed("workflow")
        if self.behavior == "unauthorized_or_out_of_scope":
            raise unauthorized("workflow")
        self.calls.append(request)


@dataclass
class FixtureEvidenceClient:
    behavior: PeerBehavior = "valid"
    bundles: dict[str, EvidenceBundle] = field(default_factory=dict)

    def get_case_evidence(self, case_id: str, *, authorization: str) -> EvidenceBundle:
        _ = authorization
        if self.behavior == "unavailable":
            raise unavailable("evidence")
        if self.behavior == "malformed":
            raise malformed("evidence")
        if self.behavior == "unauthorized_or_out_of_scope":
            raise unauthorized("evidence")
        if case_id in self.bundles:
            return self.bundles[case_id]
        return EvidenceBundle(
            contract_version=CONTRACT_VERSION,
            case_id=case_id,
            evidence=(),
            reconciliation_codes=(),
        )


@dataclass
class FixtureLedgerClient:
    behavior: PeerBehavior = "valid"
    last_authorization: str | None = None
    last_request: DecisionRequest | None = None

    def decide(self, action_id: str, request: DecisionRequest, *, authorization: str) -> Approval:
        self.last_authorization = authorization
        self.last_request = request
        if self.behavior == "unavailable":
            raise unavailable("action-ledger")
        if self.behavior == "malformed":
            raise malformed("action-ledger")
        if self.behavior == "unauthorized_or_out_of_scope":
            raise unauthorized("action-ledger")
        # Extract reviewer from bearer token suffix when present in tests.
        reviewer = "unknown"
        if authorization.startswith("Bearer "):
            reviewer = authorization.removeprefix("Bearer ").strip() or "unknown"
        return Approval(
            approval_id=f"apr-{action_id}",
            action_digest=request.action_digest,
            case_revision=request.case_revision,
            policy_version=request.policy_version,
            decision=request.decision,
            reviewer_id=reviewer,
            expires_at=request.expires_at,
        )


@dataclass
class FixtureVerifierClient:
    behavior: PeerBehavior = "valid"
    assessments: dict[str, VerificationResult] = field(default_factory=dict)

    def get_assessment(self, assessment_id: str, *, authorization: str) -> VerificationResult:
        _ = authorization
        if self.behavior == "unavailable":
            raise unavailable("verifier")
        if self.behavior == "malformed":
            raise malformed("verifier")
        if self.behavior == "unauthorized_or_out_of_scope":
            raise unauthorized("verifier")
        if assessment_id not in self.assessments:
            raise unavailable("verifier")
        return self.assessments[assessment_id]


def sample_verified_assessment(
    *,
    assessment_id: str,
    case_id: str,
    case_revision: int,
    action_id: str,
    assessed_at: str = "2026-11-13T10:00:00Z",
    expires_at: str = "2099-01-01T00:00:00Z",
) -> VerificationResult:
    evidence: list[dict[str, Any]] = [
        {
            "evidence_id": "evidence-refund",
            "case_id": case_id,
            "source": "simulator",
            "subject_ref": "subject-demo",
            "observed_at": assessed_at,
            "expires_at": expires_at,
            "digest": "abc",
            "verification_status": "VERIFIED",
            "facts": {
                "kind": "REFUND",
                "refund": {
                    "action_id": action_id,
                    "provider_ref": "prov-1",
                    "transaction_ref": "TXN-B",
                    "amount_minor": 150000,
                    "currency": "INR",
                    "status": "PROVIDER_CONFIRMED",
                },
            },
        },
        {
            "evidence_id": "evidence-credit",
            "case_id": case_id,
            "source": "simulator",
            "subject_ref": "subject-demo",
            "observed_at": assessed_at,
            "expires_at": expires_at,
            "digest": "def",
            "verification_status": "VERIFIED",
            "facts": {
                "kind": "CREDIT",
                "credit": {"provider_ref": "prov-1", "confirmed": True, "observed_at": assessed_at},
            },
        },
    ]
    return VerificationResult(
        assessment_id=assessment_id,
        case_id=case_id,
        case_revision=case_revision,
        action_id=action_id,
        assessed_at=assessed_at,
        expires_at=expires_at,
        status="VERIFIED",
        evidence=tuple(evidence),
        reason_codes=("DUPLICATE_PAYMENT_CREDITED",),
    )
