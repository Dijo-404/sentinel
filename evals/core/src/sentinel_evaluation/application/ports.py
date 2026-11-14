from __future__ import annotations

from typing import Any, Protocol

from sentinel_evaluation.domain.models import CandidateObservation, EvalFixture


class FixtureDataset(Protocol):
    version: str
    sha256: str

    def fixtures(self) -> list[EvalFixture]: ...


class CandidateRunner(Protocol):
    candidate_id: str
    model_mode: str

    def run(self, fixture: EvalFixture) -> CandidateObservation: ...


class AssemblyPeer(Protocol):
    """core-assembly.v1 probe. Real-peer mode must not silently fall back."""

    def probe(self) -> dict[str, Any]: ...


class ReportStore(Protocol):
    """Durable evaluation.v1 RunReport rows for HTTP serve/query."""

    def put_report(self, report: dict[str, Any]) -> dict[str, Any]: ...

    def get_report(self, run_id: str) -> dict[str, Any] | None: ...

    def list_reports(self) -> tuple[dict[str, Any], ...]: ...
