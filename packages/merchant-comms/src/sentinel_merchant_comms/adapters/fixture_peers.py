"""Labeled fixture peers for local preview. Not product release evidence."""

from __future__ import annotations

from dataclasses import dataclass

from sentinel_merchant_comms.application.errors import (
    PeerMalformedError,
    PeerUnauthorizedError,
    PeerUnavailableError,
)
from sentinel_merchant_comms.domain.templates import FAKE_LABEL, render_status_body
from sentinel_merchant_comms.domain.types import CONTRACT_VERSION, Case, Language, Principal

CASE_PEER = "case-api.v1"
INDIC_PEER = "indic-context.v1"

DEMO_CASE = Case(
    contract_version=CONTRACT_VERSION,
    case_id="case-demo-42",
    revision=2,
    status="WAITING_APPROVAL",
    language="en-IN",
    intent="DUPLICATE_PAYMENT",
    evidence_ids=["evidence-payment-b", "evidence-order"],
    action_id="action-demo-1",
)


@dataclass(frozen=True)
class IndicDraftResult:
    body: str
    evidence_mode: str


class FixtureCaseApi:
    """In-process case-api.v1 double. Mode is always fixture."""

    port = CASE_PEER
    mode = "fixture"

    def __init__(self, case: Case | None = None) -> None:
        self._case = case or DEMO_CASE

    def get_case(self, case_id: str, principal: Principal) -> Case:
        _ = principal
        if case_id != self._case.case_id:
            raise PeerUnauthorizedError(CASE_PEER, "case not in authenticated scope")
        return self._case


class UnavailableCaseApi:
    port = CASE_PEER
    mode = "fixture"

    def get_case(self, case_id: str, principal: Principal) -> Case:
        _ = case_id, principal
        raise PeerUnavailableError(CASE_PEER, "case-api peer not reachable")


class MalformedCaseApi:
    port = CASE_PEER
    mode = "fixture"

    def get_case(self, case_id: str, principal: Principal) -> Case:
        _ = case_id, principal
        raise PeerMalformedError(CASE_PEER, "response failed Case validation")


class UnauthorizedCaseApi:
    port = CASE_PEER
    mode = "fixture"

    def get_case(self, case_id: str, principal: Principal) -> Case:
        _ = case_id, principal
        raise PeerUnauthorizedError(CASE_PEER, "case not in authenticated scope")


class FixtureIndicContext:
    """Optional indic-context.v1 double producing labeled fake-inference text."""

    port = INDIC_PEER
    mode = "fixture"

    def draft_status(
        self, *, case: Case, language: Language, principal: Principal
    ) -> IndicDraftResult:
        _ = principal
        body = f"{FAKE_LABEL} [{language}] Indic fixture draft for {case.case_id} ({case.status})."
        return IndicDraftResult(body=body, evidence_mode="fake-inference")


class UnavailableIndicContext:
    port = INDIC_PEER
    mode = "fixture"

    def draft_status(
        self, *, case: Case, language: Language, principal: Principal
    ) -> IndicDraftResult:
        _ = case, language, principal
        raise PeerUnavailableError(INDIC_PEER, "indic-context peer not reachable")


class MalformedIndicContext:
    port = INDIC_PEER
    mode = "fixture"

    def draft_status(
        self, *, case: Case, language: Language, principal: Principal
    ) -> IndicDraftResult:
        _ = case, language, principal
        raise PeerMalformedError(INDIC_PEER, "missing ModelResult fields")


class UnauthorizedIndicContext:
    port = INDIC_PEER
    mode = "fixture"

    def draft_status(
        self, *, case: Case, language: Language, principal: Principal
    ) -> IndicDraftResult:
        _ = case, language, principal
        raise PeerUnauthorizedError(INDIC_PEER, "indic principal denied")


class TemplateOnlyIndic:
    """Helper that mirrors deterministic template output with fake label."""

    def draft_status(
        self, *, case: Case, language: Language, principal: Principal
    ) -> IndicDraftResult:
        _ = principal
        return IndicDraftResult(
            body=render_status_body(case, language, labeled_fake=True),
            evidence_mode="fake-inference",
        )
