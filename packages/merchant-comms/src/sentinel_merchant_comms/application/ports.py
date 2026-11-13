"""Narrow ports for case lookup, optional Indic drafting, storage, and clock."""

from __future__ import annotations

from typing import Protocol

from sentinel_merchant_comms.domain.types import Case, CommsDraft, Language, Principal


class CaseApiPort(Protocol):
    """Required peer. Failures must stay visible; never silent fixture fallback."""

    def get_case(self, case_id: str, principal: Principal) -> Case: ...


class IndicDraft(Protocol):
    body: str
    evidence_mode: str


class IndicContextPort(Protocol):
    """Optional peer. Unavailable/malformed falls back to labeled fake templates."""

    def draft_status(
        self, *, case: Case, language: Language, principal: Principal
    ) -> IndicDraft: ...


class DraftStorePort(Protocol):
    def save(self, draft: CommsDraft) -> CommsDraft: ...

    def get(self, draft_id: str) -> CommsDraft | None: ...


class ClockPort(Protocol):
    def now_rfc3339(self) -> str: ...


class IdGeneratorPort(Protocol):
    def new_draft_id(self) -> str: ...
