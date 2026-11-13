"""Generate, approve, reject, and simulate-send merchant status drafts."""

from __future__ import annotations

from dataclasses import dataclass

from sentinel_merchant_comms.application.errors import (
    ConflictError,
    ForbiddenError,
    MerchantCommsError,
    NotFoundError,
    PeerMalformedError,
    PeerUnauthorizedError,
    PeerUnavailableError,
    UnauthorizedError,
)
from sentinel_merchant_comms.application.ports import (
    CaseApiPort,
    ClockPort,
    DraftStorePort,
    IdGeneratorPort,
    IndicContextPort,
)
from sentinel_merchant_comms.domain import drafts as draft_rules
from sentinel_merchant_comms.domain.templates import FAKE_LABEL, render_status_body
from sentinel_merchant_comms.domain.types import (
    CommsDraft,
    Language,
    Principal,
)


@dataclass(frozen=True)
class IndicBody:
    body: str
    evidence_mode: str


OPERATOR_ROLES = frozenset({"operator", "supervisor"})


class MerchantCommsService:
    """Models propose text only. No ledger writes, refunds, or payment authority."""

    def __init__(
        self,
        *,
        case_api: CaseApiPort,
        store: DraftStorePort,
        clock: ClockPort,
        ids: IdGeneratorPort,
        indic: IndicContextPort | None = None,
        default_channel: str = "merchant-portal",
    ) -> None:
        self._case_api = case_api
        self._store = store
        self._clock = clock
        self._ids = ids
        self._indic = indic
        self._default_channel = default_channel

    def create_draft(
        self,
        *,
        case_id: str,
        language: Language,
        principal: Principal,
        channel: str | None = None,
    ) -> CommsDraft:
        _ = channel  # reserved for future channel-specific templates
        authorize_operator(principal, case_id)
        case = self._case_api.get_case(case_id, principal)
        body, _mode = self._compose_body(case=case, language=language, principal=principal)
        draft = CommsDraft(
            draft_id=self._ids.new_draft_id(),
            case_id=case.case_id,
            language=language,
            body=body,
            status="DRAFT",
            delivery_history=[],
        )
        return self._store.save(draft)

    def decide(
        self,
        *,
        draft_id: str,
        decision: str,
        principal: Principal,
    ) -> CommsDraft:
        draft = self._require_draft(draft_id)
        authorize_operator(principal, draft.case_id)
        try:
            if decision == "APPROVE":
                updated = draft_rules.approve(draft)
            elif decision == "REJECT":
                updated = draft_rules.reject(draft)
            else:
                raise ConflictError("INVALID_DECISION", f"Unknown decision {decision}")
        except draft_rules.DraftTransitionError as exc:
            raise ConflictError(exc.code, exc.message) from exc
        return self._store.save(updated)

    def simulate_send(
        self,
        *,
        draft_id: str,
        principal: Principal,
        channel: str | None = None,
    ) -> CommsDraft:
        draft = self._require_draft(draft_id)
        authorize_operator(principal, draft.case_id)
        try:
            updated = draft_rules.simulate_send(
                draft,
                at=self._clock.now_rfc3339(),
                channel=channel or self._default_channel,
            )
        except draft_rules.DraftTransitionError as exc:
            raise ConflictError(exc.code, exc.message) from exc
        return self._store.save(updated)

    def get_draft(self, draft_id: str, principal: Principal) -> CommsDraft:
        draft = self._require_draft(draft_id)
        authorize_operator(principal, draft.case_id)
        return draft

    def _require_draft(self, draft_id: str) -> CommsDraft:
        draft = self._store.get(draft_id)
        if draft is None:
            raise NotFoundError("Draft not found")
        return draft

    def _compose_body(
        self,
        *,
        case,
        language: Language,
        principal: Principal,
    ) -> tuple[str, str]:
        if self._indic is None:
            return render_status_body(case, language, labeled_fake=True), "fake"

        try:
            proposal = self._indic.draft_status(case=case, language=language, principal=principal)
        except (PeerUnavailableError, PeerMalformedError, PeerUnauthorizedError):
            # Optional peer: labeled deterministic fallback; never pretend live success.
            return render_status_body(case, language, labeled_fake=True), "fake"
        except MerchantCommsError:
            raise

        body = proposal.body.strip()
        mode = proposal.evidence_mode
        if mode == "fake-inference" and FAKE_LABEL not in body:
            body = f"{FAKE_LABEL} {body}".strip()
        return body, mode


def authorize_operator(principal: Principal, case_id: str) -> None:
    if not principal.principal_id or not principal.tenant_id:
        raise UnauthorizedError("principal incomplete")
    if not OPERATOR_ROLES.intersection(principal.roles):
        raise ForbiddenError("operator or supervisor role required")
    if "*" not in principal.case_ids and case_id not in principal.case_ids:
        raise ForbiddenError("case not in principal scope")
